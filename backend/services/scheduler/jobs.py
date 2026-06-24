import asyncio
import re
from datetime import datetime, timezone, timedelta

_SOLANA_ADDRESS_RE = re.compile(r"^[1-9A-HJ-NP-Za-km-z]{43,44}$")

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
from services import metrics
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
                if not _SOLANA_ADDRESS_RE.match(token.mint_address or ""):
                    logger.warning("Scheduler skipping invalid mint", mint=token.mint_address)
                    continue
                try:
                    total_supply = token.total_supply if token else None
                    await tracker.fetch_and_store(token.mint_address, total_supply)
                    logger.info("Scheduled holder refresh done", token=token.mint_address)
                except Exception as e:
                    logger.error("Holder refresh failed for token", token=token.mint_address, error=str(e))
        finally:
            await helius.close()


async def _trigger_signal_eval_for_smart_wallets() -> None:
    """After rescoring, push tokens with smart-wallet BUY activity (last 2h) to signal_eval_queue."""
    from sqlalchemy import text
    from config.settings import get_settings
    from config.constants import SMART_WALLET_SCORE_THRESHOLD_COLD, SMART_WALLET_SCORE_THRESHOLD
    settings = get_settings()
    threshold = (
        SMART_WALLET_SCORE_THRESHOLD_COLD
        if settings.app.signal_cold_start_mode
        else SMART_WALLET_SCORE_THRESHOLD
    )
    cutoff = datetime.now(timezone.utc) - timedelta(hours=2)
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                text("""
                    SELECT DISTINCT t.token_mint
                    FROM trades t
                    JOIN wallets w ON t.wallet_address = w.address
                    WHERE t.side = 'BUY'
                      AND t.timestamp >= :cutoff
                      AND w.composite_score >= :threshold
                """),
                {"cutoff": cutoff, "threshold": threshold},
            )
            mints = [row[0] for row in result.fetchall()]
        if mints:
            redis = await get_redis()
            for mint in mints:
                await redis.lpush("signal_eval_queue", mint)
            logger.info("Signal re-eval queued after rescore", tokens=len(mints))
    except Exception as e:
        logger.error("Signal re-eval trigger failed", error=str(e))


async def _rescore_wallets():
    async with AsyncSessionLocal() as session:
        wallet_repo = WalletRepository(session)
        high_score_wallets = await wallet_repo.list_high_score(min_score=0.0, limit=2000)
        analyzer = BehaviorAnalyzer(session)
        rescored = skipped = failed = 0
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
                if composite is None:
                    skipped += 1
                    metrics.increment("wallets_rescore_skipped_total")
                    continue
                await wallet_repo.update_scores(
                    wallet.address,
                    entry_timing_score=timing,
                    consistency_score=consistency,
                    composite_score=composite,
                    score_updated_at=datetime.now(timezone.utc),
                )
                rescored += 1
                metrics.increment("wallets_rescored_total")
                logger.info("Wallet rescored", wallet=wallet.address, composite=composite)
            except Exception as e:
                failed += 1
                metrics.increment("wallets_rescore_failed_total")
                logger.error("Wallet rescoring failed", wallet=wallet.address, error=str(e))
        logger.info(
            "Rescore cycle done",
            selected=len(high_score_wallets),
            rescored=rescored,
            skipped=skipped,
            failed=failed,
        )
    if rescored > 0:
        await _trigger_signal_eval_for_smart_wallets()


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


async def _refresh_trades():
    async with AsyncSessionLocal() as session:
        from services.trades.trade_poller import TradePoller
        poller = TradePoller(session)
        try:
            results = await poller.poll_all_tracked(limit=30)
            total = sum(results.values())
            logger.info("Scheduled trade poll done", tokens=len(results), enqueued=total)
        except Exception as e:
            logger.error("Trade poll failed", error=str(e))
        finally:
            await poller.close()


async def _purge_old_snapshots():
    """Delete holder snapshots older than 24hrs. Runs every 6hrs."""
    from sqlalchemy import text
    async with AsyncSessionLocal() as session:
        try:
            result = await session.execute(text(
                "DELETE FROM holder_snapshots WHERE snapshot_at < NOW() - INTERVAL '24 hours'"
            ))
            await session.commit()
            logger.info("Snapshot purge done", deleted=result.rowcount)
        except Exception as e:
            logger.error("Snapshot purge failed", error=str(e))


async def _ingest_pumpfun():
    # Pumpfun ingestion handled by PumpfunListener WebSocket stream in workers process
    pass


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
        _purge_old_snapshots,
        trigger=IntervalTrigger(hours=6),
        id="purge_snapshots",
        replace_existing=True,
        max_instances=1,
    )
    _scheduler.add_job(
        _refresh_trades,
        trigger=IntervalTrigger(seconds=60),
        id="refresh_trades",
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
