import asyncio
import pytest
from httpx import AsyncClient, ASGITransport


@pytest.fixture(scope="session")
def event_loop():
    """Single event loop for the integration test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def client():
    """Shared HTTP client; app lifespan runs once per session."""
    import api.main
    api.main._SCHEDULER_AVAILABLE = False
    from api.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
