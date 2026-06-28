import asyncio
import json

from core.db import AsyncSessionLocal
from core.redis import get_redis
from services.pumpfun.launch_tracker import PumpfunTracker
from config.logging import get_logger

logger = get_logger(__name__)

PUMPFUN_LAUNCH_QUEUE = "pumpfun_launch_queue"
HOLDER_UPDATE_QUEUE = "holder_update_queue"
SIGNAL_EVAL_QUEUE = "signal_eval_queue"


async def process_launch(raw: dict) -> None:
    async with AsyncSessionLocal() as session:
        tracker = PumpfunTracker(session)
        try:
            token = await tracker.process_raw_launch(raw)
            if token is None:
                return
            mint = token.mint_address if hasattr(token, "mint_address") else str(token)
            redis = await get_redis()
            # Enqueue downstream: holder refresh + signal evaluation
            await redis.lpush(HOLDER_UPDATE_QUEUE, mint)
            await redis.lpush(SIGNAL_EVAL_QUEUE, mint)
            logger.info("Pump.fun launch processed and downstream enqueued", mint=mint)

            # Archive token create — fire-and-forget
            from services.archive import archive_publish
            await archive_publish("token", {
                "mint": mint,
                "name": raw.get("name"),
                "symbol": raw.get("symbol"),
                "creator": raw.get("traderPublicKey") or raw.get("txSigner") or raw.get("creator"),
                "created_at": raw.get("timestamp"),
                "metadata_uri": raw.get("uri") or raw.get("metadataUri"),
            })
            await archive_publish("pumpapi_event", {"event_type": "create", "raw": raw})
        finally:
            await tracker.close()


async def run_pumpfun_worker():
    from shared.heartbeat import beat
    logger.info("Pump.fun worker starting")
    redis = await get_redis()
    while True:
        try:
            await beat("pumpfun")
            result = await redis.brpop(PUMPFUN_LAUNCH_QUEUE, timeout=10)
            if not result:
                continue
            _, raw_json = result
            if isinstance(raw_json, bytes):
                raw_json = raw_json.decode("utf-8")
            raw = json.loads(raw_json)
            await process_launch(raw)
        except Exception as e:
            logger.error("Pump.fun worker loop error", error=str(e))
            await asyncio.sleep(2)
