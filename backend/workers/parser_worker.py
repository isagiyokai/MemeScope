import asyncio
import json
from datetime import datetime, timezone

import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession

from core.db import AsyncSessionLocal
from core.redis import get_redis
from clients.helius_client import HeliusClient
from services.parser.event_normalizer import normalize_event
from repositories.trade_repo import TradeRepository
from repositories.wallet_repo import WalletRepository
from schemas.trade_schema import TradeCreate
from schemas.wallet_schema import WalletCreate
from config.logging import get_logger

logger = get_logger(__name__)

RAW_TX_QUEUE = "raw_tx_queue"
PARSED_TRADE_QUEUE = "parsed_trade_queue"
SIGNAL_EVAL_QUEUE = "signal_eval_queue"


_SOLANA_SIG_RE = __import__("re").compile(r"^[1-9A-HJ-NP-Za-km-z]{64,88}$")


async def process_raw_tx(raw: dict) -> None:
    if not isinstance(raw, dict):
        logger.warning("Skipping non-dict queue item")
        return

    signature = raw.get("signature")
    tx = raw.get("transaction", {})
    slot = raw.get("slot")

    # Validate signature format before touching the DB or downstream services
    if signature and not _SOLANA_SIG_RE.match(str(signature)):
        logger.warning("Skipping tx with invalid signature format", sig=str(signature)[:20])
        return

    if not signature or not tx:
        logger.warning("Skipping invalid raw tx", raw=raw)
        return

    event = normalize_event(tx, signature, slot)
    if not event:
        return

    async with AsyncSessionLocal() as session:
        trade_repo = TradeRepository(session)
        try:
            trade = await trade_repo.create(TradeCreate(**event))
            logger.info("Trade parsed and stored", tx=signature, token=event["token_mint"], side=event["side"])

            # Enqueue signal evaluation
            redis = await get_redis()
            await redis.lpush(SIGNAL_EVAL_QUEUE, event["token_mint"])

            # Archive — fire-and-forget, never raises
            from services.archive import archive_publish
            ts = event.get("timestamp")
            await archive_publish("trade", {
                "signature": signature,
                "token_mint": event.get("token_mint"),
                "wallet": event.get("wallet_address"),
                "side": event.get("side"),
                "sol_amount": event.get("sol_amount"),
                "token_amount": event.get("token_amount"),
                "timestamp": ts.isoformat() if isinstance(ts, datetime) else ts,
                "source": event.get("source", "unknown"),
            })
        except Exception as e:
            logger.error("Failed to store trade", tx=signature, error=str(e))
            await session.rollback()
            return

    # Ensure wallet stub exists with composite_score=0.0 so rescore job picks it up.
    # Separate session so trade commit is not rolled back on wallet conflict.
    wallet_address = event.get("wallet_address")
    if wallet_address:
        async with AsyncSessionLocal() as wsession:
            wallet_repo = WalletRepository(wsession)
            try:
                existing = await wallet_repo.get_by_address(wallet_address)
                if not existing:
                    await wallet_repo.create(WalletCreate(address=wallet_address, composite_score=0.0))
                    logger.debug("Wallet stub created", wallet=wallet_address)
            except Exception as e:
                logger.error("Failed to create wallet stub", wallet=wallet_address, error=str(e))


async def run_parser_worker():
    from shared.heartbeat import beat
    logger.info("Parser worker starting")
    redis = await get_redis()
    while True:
        try:
            await beat("parser")
            result = await redis.brpop(RAW_TX_QUEUE, timeout=5)
            if not result:
                continue
            _, raw_json = result
            raw = json.loads(raw_json)
            await process_raw_tx(raw)
        except Exception as e:
            logger.error("Parser worker loop error", error=str(e))
            await asyncio.sleep(2)
