"""Worker liveness heartbeat via Redis.

Each worker calls beat() every loop. The health endpoint reads these keys
to report whether workers are alive or stale.

Key format : heartbeat:{worker_name}
Value      : Unix timestamp (int) of last beat
TTL        : 2× BEAT_INTERVAL — if the key expires the worker is considered dead
"""
import time

BEAT_INTERVAL = 30      # seconds between beats
BEAT_TTL = 90           # key expires after 3 missed beats → worker is dead

WORKER_NAMES = ("parser", "signal", "holder", "pumpfun")


async def beat(name: str) -> None:
    """Set heartbeat key for *name*. Call once per worker loop iteration."""
    try:
        from core.redis import get_redis
        redis = await get_redis()
        await redis.set(f"heartbeat:{name}", int(time.time()), ex=BEAT_TTL)
    except Exception:
        pass  # never let a heartbeat failure crash the worker


async def get_worker_status() -> dict[str, dict]:
    """Return liveness status for all known workers."""
    result: dict[str, dict] = {}
    try:
        from core.redis import get_redis
        redis = await get_redis()
        for name in WORKER_NAMES:
            val = await redis.get(f"heartbeat:{name}")
            if val is None:
                result[name] = {"status": "dead"}
            else:
                age_s = int(time.time()) - int(val)
                result[name] = {
                    "status": "ok" if age_s <= BEAT_TTL else "stale",
                    "last_beat_s": age_s,
                }
    except Exception:
        for name in WORKER_NAMES:
            result[name] = {"status": "unknown"}
    return result
