import asyncio
import pytest
from httpx import AsyncClient, ASGITransport


@pytest.fixture(scope="session")
def event_loop():
    """Single event loop for entire integration test session — required for asyncpg pool reuse."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def no_scheduler(monkeypatch_session):
    """Disable APScheduler to prevent background DB jobs racing with test queries."""
    import api.main
    monkeypatch_session.setattr(api.main, "_SCHEDULER_AVAILABLE", False)


@pytest.fixture(scope="session")
async def client():
    """Single shared HTTP client for all integration tests. App lifespan runs once."""
    import api.main
    api.main._SCHEDULER_AVAILABLE = False  # disable scheduler before lifespan starts
    from api.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
