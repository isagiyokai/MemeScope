from datetime import datetime, timezone, timedelta
from typing import Sequence, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from models.holder_snapshot import HolderSnapshot
from schemas.holder_schema import HolderSnapshotRead
from repositories.holder_repo import HolderRepository
from config.logging import get_logger

logger = get_logger(__name__)


class HolderSnapshotService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = HolderRepository(session)

    async def save_snapshot(self, snapshot: HolderSnapshotRead) -> HolderSnapshot:
        from schemas.holder_schema import HolderSnapshotCreate
        data = HolderSnapshotCreate(
            token_mint=snapshot.token_mint,
            wallet_address=snapshot.wallet_address,
            rank=snapshot.rank,
            balance=snapshot.balance,
            pct_supply=snapshot.pct_supply,
            change_24h=snapshot.change_24h,
            change_7d=snapshot.change_7d,
            snapshot_at=snapshot.snapshot_at,
        )
        return await self.repo.create(data)
