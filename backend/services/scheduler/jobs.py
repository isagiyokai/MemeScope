import asyncio
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from core.db import AsyncSessionLocal
from core.redis import get_redis
from clients.helius_client import HeliusClient
from services.holders.top10_tracker import Top10Tracker
from services.wallet_intelligence.behavior_analyzer import BehaviorAnalyzer
from services.signals.signal_engine import SignalEngine
from services.clustering.cluster_detector import ClusterDetector
from services.scheduler.pumpfun_job import enqueue_pumpfun_launches
from repositories.token_repo import TokenRepository
from repositories.wallet_repo import WalletRepository
from config.logging import get_logger
from config.constants import (
    HOLDER_SNAPSHOT_INTERVAL_SECONDS,
    PRICE_POLL_INTERVAL_SECONDS,
    SIGNAL_EVAL_INTERVAL_SECONDS,
)

logger = get_logger(__name__)

_scheduler: AsyncIOScheduler | None = None


async def _refresh_holders():
    async with AsyncSessionLocal() as session:
        token_repo = TokenRepository(session)
        tokens = await token_repo.list_tracking(limit=500)
        if not tokens:
            return
        helius = HeliusClient()
        try:
            tracker = Top10Tracker(session, helius)
            for token in tokens:
                try:
                    total_supply = token.total_supply if token else None
                    await tracker.fetch_and_store(token.mint_address, total_supply)
                    logger.info("Scheduled holder refresh done", token=token.mint_address)
                except Exception as e:
                    logger.error("Holder refresh failed for token", token=token.mint_address, error=str(e))
        finally:
            await helius.close()


async def _rescore_wallets():
    async with AsyncSessionLocal() as session:
        wallet_repo = WalletRepository(session)
        high_score_wallets = await wallet_repo.list_high_score(min_score=0.0, limit=500)
        analyzer = BehaviorAnalyzer(session)
        for wallet in high_score_wallets:
            try:
                timing = await analyzer.entry_timing_score(wallet.address)
                consistency = await analyzer.consistency_score(wallet.address)
                composite = await analyzer.composite_score(
                    wallet.address,
                    win_rate=wallet.win_rate,
                    avg_roi=wallet.avg_roi,
                    timing=timing,
                    consistency=consistency,
                )
                await wallet_repo.update_scores(
                    wallet.address,
                    entry_timing_score=timing,
                    consistency_score=consistency,
                    composite_score=composite,
                    score_updated_at=datetime.now(timezone.utc),
                )
                logger.info("Wallet rescored", wallet=wallet.address, composite=composite)
            except Exception as e:
                logger.error("Wallet rescoring failed", wallet=wallet.address, error=str(e))


async def _evaluate_signals():
    async with AsyncSessionLocal() as session:
        engine = SignalEngine(session)
        try:
            signals = await engine.evaluate_all_tracked()
            logger.info("Scheduled signal evaluation done", signals=len(signals))
        except Exception as e:
            logger.error("Signal evaluation failed", error=str(e))


async def _detect_clusters():
    async with AsyncSessionLocal() as session:
        detector = ClusterDetector(session)
        try:
            clusters = await detector.run()
            logger.info("Scheduled cluster detection done", clusters=len(clusters))
        except Exception as e:
            logger.error("Cluster detection failed", error=str(e))


async def _ingest_pumpfun():
    try:
        enqueued = await enqueue_pumpfun_launches()
        logger.info("Scheduled Pump.fun ingestion done", enqueued=enqueued)
    except Exception as e:
        logger.error("Pump.fun ingestion failed", error=str(e))


def start_scheduler():
    global _scheduler
    if _scheduler is not None:
        logger.warning("Scheduler already started")
        return
    _scheduler = AsyncIOScheduler()

    _scheduler.add_job(
        _refresh_holders,
        trigger=IntervalTrigger(seconds=HOLDER_SNAPSHOT_INTERVAL_SECONDS),
        id="refresh_holders",
        replace_existing=True,
        max_instances=1,
    )
    _scheduler.add_job(
        _rescore_wallets,
        trigger=IntervalTrigger(minutes=5),
        id="rescore_wallets",
        replace_existing=True,
        max_instances=1,
    )
    _scheduler.add_job(
        _evaluate_signals,
        trigger=IntervalTrigger(seconds=SIGNAL_EVAL_INTERVAL_SECONDS),
        id="evaluate_signals",
        replace_existing=True,
        max_instances=1,
    )
    _scheduler.add_job(
        _detect_clusters,
        trigger=IntervalTrigger(minutes=10),
        id="detect_clusters",
        replace_existing=True,
        max_instances=1,
    )
    _scheduler.add_job(
        _ingest_pumpfun,
        trigger=IntervalTrigger(seconds=30),
        id="ingest_pumpfun",
        replace_existing=True,
        max_instances=1,
    )

    _scheduler.start()
    logger.info("Scheduler started", jobs=len(_scheduler.get_jobs()))


def shutdown_scheduler():
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("Scheduler shut down")
