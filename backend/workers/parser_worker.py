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
from schemas.trade_schema import TradeCreate
from config.logging import get_logger

logger = get_logger(__name__)

RAW_TX_QUEUE = "raw_tx_queue"
PARSED_TRADE_QUEUE = "parsed_trade_queue"
SIGNAL_EVAL_QUEUE = "signal_eval_queue"


async def process_raw_tx(raw: dict) -> None:
    signature = raw.get("signature")
    tx = raw.get("transaction", {})
    slot = raw.get("slot")

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
        except Exception as e:
            logger.error("Failed to store trade", tx=signature, error=str(e))
            await session.rollback()


async def run_parser_worker():
    logger.info("Parser worker starting")
    redis = await get_redis()
    while True:
        try:
            result = await redis.brpop(RAW_TX_QUEUE, timeout=5)
            if not result:
                continue
            _, raw_json = result
            raw = json.loads(raw_json)
            await process_raw_tx(raw)
        except Exception as e:
            logger.error("Parser worker loop error", error=str(e))
            await asyncio.sleep(2)
