from datetime import datetime, timezone
from typing import Optional, Any

from sqlalchemy.ext.asyncio import AsyncSession

from clients.pumpapi_client import PumpAPIClient
from repositories.wallet_repo import WalletRepository
from schemas.wallet_schema import WalletCreate
from config.logging import get_logger

logger = get_logger(__name__)


class CreatorTracker:
    """
    Tracks creator wallets for Pump.fun launches.
    Queries PumpAPI for creator metadata and tags the creator wallet.
    """

    def __init__(self, session: AsyncSession, client: Optional[PumpAPIClient] = None):
        self.session = session
        self.client = client or PumpAPIClient()
        self.wallet_repo = WalletRepository(session)

    async def ingest_creator(self, mint: str) -> Optional[Any]:
        """Fetch creator info from PumpAPI and persist the creator wallet."""
        try:
            data = await self.client.get_creator(mint)
        except Exception as e:
            logger.error("PumpAPI creator fetch failed", mint=mint, error=str(e))
            return None

        if not data:
            return None

        creator = data.get("creator") or data.get("creator_wallet") or data.get("address")
        if not creator:
            logger.warning("Creator data missing address", mint=mint, data=data)
            return None

        existing = await self.wallet_repo.get_by_address(creator)
        if not existing:
            try:
                wallet = await self.wallet_repo.create(
                    WalletCreate(address=creator, tags="creator,pumpfun")
                )
                logger.info("Creator wallet persisted", mint=mint, wallet=creator)
                return wallet
            except Exception as e:
                logger.error("Failed to persist creator wallet", wallet=creator, error=str(e))
                return None
        else:
            # Tag existing if not already tagged
            tags = existing.tags or ""
            if "creator" not in tags:
                new_tags = (tags + ",creator,pumpfun").strip(",")
                await self.wallet_repo.update_scores(
                    creator, tags=new_tags, last_active=datetime.now(timezone.utc)
                )
                logger.info("Creator tag added to existing wallet", mint=mint, wallet=creator)
            return existing

    async def close(self):
        await self.client.close()
