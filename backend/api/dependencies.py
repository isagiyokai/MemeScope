from typing import AsyncGenerator, Optional

from fastapi import Depends, Header, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.db import AsyncSessionLocal
from core.redis import get_redis
from config.settings import get_settings


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def get_redis_client():
    return await get_redis()


async def require_api_key(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
) -> None:
    """Require X-API-Key header when APP_API_KEY is configured. No-op if key not set."""
    configured = get_settings().app.api_key
    if not configured:
        return
    if x_api_key != configured:
        raise HTTPException(status_code=403, detail="Invalid or missing API key")
