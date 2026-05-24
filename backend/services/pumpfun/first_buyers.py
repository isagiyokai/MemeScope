from datetime import datetime, timezone
from typing import Optional, Any

from sqlalchemy.ext.asyncio import AsyncSession

from clients.pumpapi_client import PumpAPIClient
from repositories.wallet_repo import WalletRepository
from schemas.wallet_schema import WalletCreate
from config.logging import get_logger

logger = get_logger(__name__)


class FirstBuyersTracker:
    """
    Tracks and persists first buyers for Pump.fun launches.
    Wraps PumpAPIClient to fetch and store early buyer wallets.
    """

    def __init__(self, session: AsyncSession, client: Optional[PumpAPIClient] = None):
        self.session = session
        self.client = client or PumpAPIClient()
        self.wallet_repo = WalletRepository(session)

    async def ingest_first_buyers(self, mint: str, limit: int = 50) -> list[Any]:
        """Fetch first buyers from PumpAPI and persist wallet stubs."""
        try:
            buyers = await self.client.get_first_buyers(mint, limit=limit)
        except Exception as e:
            logger.error("PumpAPI first buyers fetch failed", mint=mint, error=str(e))
            return []

        created = []
        for buyer in buyers:
            addr = buyer.get("wallet") or buyer.get("buyer") or buyer.get("address")
            if not addr:
                continue
            existing = await self.wallet_repo.get_by_address(addr)
            if not existing:
                try:
                    wallet = await self.wallet_repo.create(WalletCreate(address=addr))
                    created.append(wallet)
                except Exception as e:
                    logger.error("Failed to persist first buyer wallet", wallet=addr, error=str(e))
        logger.info("First buyers ingested", mint=mint, new=len(created), total=len(buyers))
        return created

    async def close(self):
        await self.client.close()
