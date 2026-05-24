import asyncio

import redis.asyncio as aioredis

from core.db import AsyncSessionLocal
from core.redis import get_redis
from services.signals.signal_engine import SignalEngine
from config.logging import get_logger

logger = get_logger(__name__)

SIGNAL_EVAL_QUEUE = "signal_eval_queue"


async def run_signal_worker():
    logger.info("Signal worker starting")
    redis = await get_redis()
    while True:
        try:
            result = await redis.brpop(SIGNAL_EVAL_QUEUE, timeout=10)
            if not result:
                continue
            _, token_mint = result
            token_mint = token_mint.decode() if isinstance(token_mint, bytes) else token_mint
            async with AsyncSessionLocal() as session:
                engine = SignalEngine(session)
                signals = await engine.evaluate_token(token_mint)
                logger.info("Signal evaluation done", token=token_mint, signals=len(signals))
        except Exception as e:
            logger.error("Signal worker loop error", error=str(e))
            await asyncio.sleep(2)
