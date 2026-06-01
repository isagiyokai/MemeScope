import asyncio
import re
from datetime import datetime, timezone

import redis.asyncio as aioredis

from core.db import AsyncSessionLocal
from core.redis import get_redis
from clients.helius_client import HeliusClient
from services.holders.top10_tracker import Top10Tracker
from repositories.token_repo import TokenRepository
from config.logging import get_logger
from config.constants import HOLDER_SNAPSHOT_INTERVAL_SECONDS

logger = get_logger(__name__)

HOLDER_UPDATE_QUEUE = "holder_update_queue"

_SOLANA_ADDRESS_RE = re.compile(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$")


async def refresh_token_holders(token_mint: str) -> None:
    if not token_mint or not _SOLANA_ADDRESS_RE.match(token_mint):
        logger.warning("Skipping invalid token mint address", mint=repr(token_mint))
        return
    async with AsyncSessionLocal() as session:
        helius = HeliusClient()
        try:
            tracker = Top10Tracker(session, helius)
            token_repo = TokenRepository(session)
            token = await token_repo.get_by_mint(token_mint)
            total_supply = token.total_supply if token else None
            await tracker.fetch_and_store(token_mint, total_supply)
            logger.info("Top10 refreshed", token=token_mint)
        finally:
            await helius.close()


async def run_holder_worker():
    from shared.heartbeat import beat
    logger.info("Holder worker starting")
    redis = await get_redis()
    while True:
        try:
            await beat("holder")
            result = await redis.brpop(HOLDER_UPDATE_QUEUE, timeout=HOLDER_SNAPSHOT_INTERVAL_SECONDS)
            if result:
                _, token_mint = result
                token_mint = token_mint.decode() if isinstance(token_mint, bytes) else token_mint
                await refresh_token_holders(token_mint)
            else:
                # No queue items: refresh all tracked tokens
                async with AsyncSessionLocal() as session:
                    token_repo = TokenRepository(session)
                    tokens = await token_repo.list_tracking(limit=500)
                for token in tokens:
                    await refresh_token_holders(token.mint_address)
                    await asyncio.sleep(1)  # Rate limit
        except Exception as e:
            logger.error("Holder worker loop error", error=str(e))
            await asyncio.sleep(2)

