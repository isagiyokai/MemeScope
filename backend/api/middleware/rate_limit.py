import time
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Sliding-window in-process rate limiter (single-instance safe).

    Default: 200 requests / 60 seconds per client IP.
    Skips rate limiting for health-check paths to avoid false alarms.
    """

    _SKIP_PATHS = {"/health", "/api/v1/health"}

    def __init__(self, app, calls: int = 200, period: int = 60):
        super().__init__(app)
        self._calls = calls
        self._period = period
        self._buckets: dict[str, deque] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next):
        if request.url.path in self._SKIP_PATHS:
            return await call_next(request)

        ip = request.client.host if request.client else "0.0.0.0"
        now = time.monotonic()
        bucket = self._buckets[ip]
        while bucket and bucket[0] < now - self._period:
            bucket.popleft()
        if len(bucket) >= self._calls:
            return JSONResponse(
                {"detail": "Too many requests"},
                status_code=429,
                headers={"Retry-After": str(self._period)},
            )
        bucket.append(now)
        return await call_next(request)
