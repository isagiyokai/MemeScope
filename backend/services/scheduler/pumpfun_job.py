import json
from typing import Optional

from clients.pumpapi_client import PumpAPIClient
from core.redis import get_redis
from config.settings import get_settings
from config.logging import get_logger

logger = get_logger(__name__)
PUMPFUN_LAUNCH_QUEUE = "pumpfun_launch_queue"

settings = get_settings()


async def enqueue_pumpfun_launches(limit: int = 50) -> int:
    """
    Fetch latest Pump.fun launches from PumpAPI and enqueue them
    to Redis for downstream worker processing.
    """
    client = PumpAPIClient()
    try:
        launches = await client.get_latest_launches(limit=limit)
    except Exception as e:
        logger.error("PumpAPI fetch failed in scheduler", error=str(e))
        return 0
    finally:
        await client.close()

    redis = await get_redis()
    enqueued = 0
    for launch in launches:
        if not isinstance(launch, dict):
            continue
        mint = launch.get("mint") or launch.get("token_mint") or launch.get("mint_address")
        if not mint:
            continue
        try:
            await redis.lpush(PUMPFUN_LAUNCH_QUEUE, json.dumps(launch))
            enqueued += 1
        except Exception as e:
            logger.error("Failed to enqueue Pump.fun launch", mint=mint, error=str(e))

    logger.info("Pump.fun launches enqueued", count=enqueued, fetched=len(launches))
    return enqueued
