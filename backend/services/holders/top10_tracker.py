from datetime import datetime, timezone
from typing import Sequence, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from clients.helius_client import HeliusClient
from models.holder_snapshot import HolderSnapshot
from schemas.holder_schema import HolderSnapshotCreate
from repositories.holder_repo import HolderRepository
from config.logging import get_logger
from config.constants import HOLDER_ACCUMULATION_THRESHOLD_PCT, SINGLE_HOLDER_CHANGE_THRESHOLD_PCT

logger = get_logger(__name__)


class Top10Tracker:
    def __init__(self, session: AsyncSession, helius: HeliusClient):
        self.session = session
        self.helius = helius
        self.holder_repo = HolderRepository(session)

    async def fetch_and_store(self, token_mint: str, total_supply: Optional[float] = None) -> Sequence[HolderSnapshot]:
        largest = await self.helius.get_token_largest_accounts(token_mint)
        if not largest:
            logger.warning("No holder data returned", token=token_mint)
            return []

        now = datetime.now(timezone.utc)
        snapshots = []
        for i, entry in enumerate(largest[:10]):
            address = entry.get("address")
            amount = entry.get("amount", "0")
            decimals = entry.get("decimals", 6)
            ui_amount = float(entry.get("uiAmount", 0))
            if not address:
                continue

            pct = (ui_amount / total_supply) if total_supply and total_supply > 0 else 0.0
            snapshots.append(HolderSnapshotCreate(
                token_mint=token_mint,
                wallet_address=address,
                rank=i + 1,
                balance=ui_amount,
                pct_supply=pct,
                change_24h=None,
                change_7d=None,
                snapshot_at=now,
            ))

        created = await self.holder_repo.bulk_create(snapshots)
        logger.info("Top10 snapshot stored", token=token_mint, count=len(created))
        return created

    async def get_latest_top10(self, token_mint: str) -> Sequence[HolderSnapshot]:
        return await self.holder_repo.list_top10(token_mint)
