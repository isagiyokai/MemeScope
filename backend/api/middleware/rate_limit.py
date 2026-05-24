import time
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Sliding-window rate limiter — Redis-backed with in-memory fallback.

    Redis path: sorted-set per IP, score = epoch-ms timestamp.
    Fallback (Redis unavailable): per-process deque, single-instance only.
    Default: 200 requests / 60 seconds per client IP.
    Health-check paths are exempt from limiting.
    """

    _SKIP_PATHS = {"/health", "/api/v1/health", "/metrics"}

    def __init__(self, app, calls: int = 200, period: int = 60):
        super().__init__(app)
        self._calls = calls
        self._period = period
        self._local: dict[str, deque] = defaultdict(deque)  # fallback

    async def dispatch(self, request: Request, call_next):
        if request.url.path in self._SKIP_PATHS:
            return await call_next(request)

        ip = request.client.host if request.client else "0.0.0.0"

        if await self._redis_check(ip):
            return JSONResponse(
                {"detail": "Too many requests"},
                status_code=429,
                headers={"Retry-After": str(self._period)},
            )

        return await call_next(request)

    async def _redis_check(self, ip: str) -> bool:
        """Returns True if this request should be rejected (limit exceeded)."""
        try:
            from core.redis import get_redis
            redis = await get_redis()
            key = f"rl:{ip}"
            now_ms = int(time.time() * 1000)
            window_start = now_ms - self._period * 1000

            async with redis.pipeline(transaction=True) as pipe:
                pipe.zremrangebyscore(key, 0, window_start)
                pipe.zadd(key, {str(now_ms): now_ms})
                pipe.zcard(key)
                pipe.expire(key, self._period + 1)
                results = await pipe.execute()

            return results[2] > self._calls
        except Exception:
            return self._local_check(ip)

    def _local_check(self, ip: str) -> bool:
        now = time.monotonic()
        bucket = self._local[ip]
        while bucket and bucket[0] < now - self._period:
            bucket.popleft()
        if len(bucket) >= self._calls:
            return True
        bucket.append(now)
        return False
