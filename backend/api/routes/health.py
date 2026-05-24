import time
import asyncio

import httpx
from fastapi import APIRouter

from config.settings import get_settings
from config.logging import get_logger
from core.db import engine
from core.redis import redis_health_check

router = APIRouter()
settings = get_settings()
logger = get_logger(__name__)


async def _check_db() -> dict:
    try:
        from sqlalchemy import text
        t0 = time.monotonic()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "ok", "latency_ms": round((time.monotonic() - t0) * 1000)}
    except Exception as e:
        logger.error("DB health check failed", error=str(e))
        return {"status": "error"}


async def _check_redis() -> dict:
    try:
        t0 = time.monotonic()
        ok = await redis_health_check()
        latency = round((time.monotonic() - t0) * 1000)
        if ok:
            return {"status": "ok", "latency_ms": latency}
        return {"status": "error"}
    except Exception as e:
        logger.error("Redis health check failed", error=str(e))
        return {"status": "error"}


async def _check_helius() -> dict:
    try:
        url = settings.helius.get_rpc_url()
        payload = {"jsonrpc": "2.0", "id": 1, "method": "getHealth", "params": []}
        t0 = time.monotonic()
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(url, json=payload)
            r.raise_for_status()
            data = r.json()
            if "error" in data:
                logger.warning("Helius health check RPC error")
                return {"status": "error"}
        return {"status": "ok", "latency_ms": round((time.monotonic() - t0) * 1000)}
    except Exception as e:
        logger.error("Helius health check failed", error=str(e))
        return {"status": "error"}


async def _check_birdeye() -> dict:
    try:
        url = f"{settings.birdeye.base_url.rstrip('/')}/defi/price?address=So11111111111111111111111111111111111111112"
        headers = {"X-API-KEY": settings.birdeye.api_key, "x-chain": "solana"}
        t0 = time.monotonic()
        async with httpx.AsyncClient(timeout=10, headers=headers) as client:
            r = await client.get(url)
            r.raise_for_status()
        return {"status": "ok", "latency_ms": round((time.monotonic() - t0) * 1000)}
    except Exception as e:
        logger.error("Birdeye health check failed", error=str(e))
        return {"status": "error"}


@router.get("")
async def api_health():
    db, redis, helius, birdeye = await asyncio.gather(
        _check_db(), _check_redis(), _check_helius(), _check_birdeye()
    )
    overall = "ok" if all(s["status"] == "ok" for s in (db, redis, helius, birdeye)) else "degraded"
    return {"overall": overall, "db": db, "redis": redis, "helius": helius, "birdeye": birdeye}
