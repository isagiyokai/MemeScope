import asyncio
import sys
import json

import httpx

from core.db import engine
from core.redis import redis_health_check
from config.settings import get_settings
from config.logging import configure_logging, get_logger

configure_logging()
logger = get_logger(__name__)
settings = get_settings()


async def check_db() -> dict:
    try:
        from sqlalchemy import text
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "ok", "service": "database"}
    except Exception as e:
        return {"status": "error", "service": "database", "error": str(e)}


async def check_redis() -> dict:
    try:
        ok = await redis_health_check()
        if ok:
            return {"status": "ok", "service": "redis"}
        return {"status": "error", "service": "redis", "error": "ping failed"}
    except Exception as e:
        return {"status": "error", "service": "redis", "error": str(e)}


async def check_helius() -> dict:
    try:
        url = settings.helius.get_rpc_url()
        payload = {"jsonrpc": "2.0", "id": 1, "method": "getHealth", "params": []}
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(url, json=payload)
            r.raise_for_status()
            data = r.json()
            if "error" in data:
                return {"status": "error", "service": "helius", "error": data["error"]}
        return {"status": "ok", "service": "helius"}
    except Exception as e:
        return {"status": "error", "service": "helius", "error": str(e)}


async def check_birdeye() -> dict:
    try:
        url = f"{settings.birdeye.base_url.rstrip('/')}/defi/price?address=So11111111111111111111111111111111111111112"
        headers = {"X-API-KEY": settings.birdeye.api_key, "x-chain": "solana"}
        async with httpx.AsyncClient(timeout=10, headers=headers) as client:
            r = await client.get(url)
            r.raise_for_status()
        return {"status": "ok", "service": "birdeye"}
    except Exception as e:
        return {"status": "error", "service": "birdeye", "error": str(e)}


async def main():
    checks = await asyncio.gather(check_db(), check_redis(), check_helius(), check_birdeye())
    result = {
        "overall": "ok" if all(c["status"] == "ok" for c in checks) else "degraded",
        "checks": checks,
    }
    print(json.dumps(result, indent=2))
    if result["overall"] != "ok":
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
