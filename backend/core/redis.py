import redis.asyncio as aioredis

from config.settings import get_settings

_settings = get_settings()
_redis_pool = None


async def get_redis():
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = aioredis.from_url(
            _settings.redis.url,
            decode_responses=_settings.redis.decode_responses,
            db=_settings.redis.db,
        )
    return _redis_pool


async def redis_health_check() -> bool:
    try:
        client = await get_redis()
        await client.ping()
        return True
    except Exception:
        return False


async def close_redis():
    global _redis_pool
    if _redis_pool is not None:
        await _redis_pool.close()
        _redis_pool = None
