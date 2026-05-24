import asyncio
import time
import pytest
from utils.rate_limiter import RateLimiter


async def test_rate_limiter_rejects_zero_rpm():
    with pytest.raises(ValueError):
        RateLimiter(rpm=0)


async def test_rate_limiter_rejects_negative_rpm():
    with pytest.raises(ValueError):
        RateLimiter(rpm=-10)


async def test_rate_limiter_first_call_no_wait():
    limiter = RateLimiter(rpm=60)
    waited = await limiter.acquire()
    assert waited == 0.0


async def test_rate_limiter_tracks_request_count():
    limiter = RateLimiter(rpm=3600)  # 1 per ms — effectively no wait
    for _ in range(5):
        await limiter.acquire()
    assert limiter.stats["total_requests"] == 5


async def test_rate_limiter_enforces_interval():
    """Two back-to-back calls at 60 RPM (1 RPS) must take >= 1s total."""
    limiter = RateLimiter(rpm=60)
    t0 = time.monotonic()
    await limiter.acquire()
    await limiter.acquire()
    elapsed = time.monotonic() - t0
    assert elapsed >= 0.95  # allow 50ms tolerance


async def test_rate_limiter_stats_structure():
    limiter = RateLimiter(rpm=60)
    await limiter.acquire()
    s = limiter.stats
    assert "rpm" in s
    assert "total_requests" in s
    assert "avg_wait_ms" in s
    assert s["rpm"] == 60
    assert s["total_requests"] == 1


async def test_high_rpm_no_significant_delay():
    """At 3600 RPM (1 req/ms) two calls complete in well under 1s."""
    limiter = RateLimiter(rpm=3600)
    t0 = time.monotonic()
    for _ in range(5):
        await limiter.acquire()
    assert time.monotonic() - t0 < 1.0
