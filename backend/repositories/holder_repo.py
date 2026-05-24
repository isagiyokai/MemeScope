from uuid import UUID
from typing import Optional, Sequence
from datetime import datetime

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from models.holder_snapshot import HolderSnapshot
from schemas.holder_schema import HolderSnapshotCreate


class HolderRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, data: HolderSnapshotCreate) -> HolderSnapshot:
        snap = HolderSnapshot(**data.model_dump(exclude_unset=True))
        self.session.add(snap)
        await self.session.commit()
        await self.session.refresh(snap)
        return snap

    async def bulk_create(self, items: list[HolderSnapshotCreate]) -> list[HolderSnapshot]:
        snaps = [HolderSnapshot(**i.model_dump(exclude_unset=True)) for i in items]
        self.session.add_all(snaps)
        await self.session.commit()
        for s in snaps:
            await self.session.refresh(s)
        return snaps

    async def get_latest_snapshot(self, token_mint: str, wallet: str) -> Optional[HolderSnapshot]:
        result = await self.session.execute(
            select(HolderSnapshot)
            .where(and_(HolderSnapshot.token_mint == token_mint, HolderSnapshot.wallet_address == wallet))
            .order_by(HolderSnapshot.snapshot_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def list_top10(self, token_mint: str, at_time: Optional[datetime] = None) -> Sequence[HolderSnapshot]:
        if at_time is None:
            subq = (
                select(func.max(HolderSnapshot.snapshot_at))
                .where(HolderSnapshot.token_mint == token_mint)
                .scalar_subquery()
            )
        else:
            subq = at_time
        result = await self.session.execute(
            select(HolderSnapshot)
            .where(and_(HolderSnapshot.token_mint == token_mint, HolderSnapshot.snapshot_at == subq))
            .order_by(HolderSnapshot.rank.asc())
            .limit(10)
        )
        return result.scalars().all()

    async def list_history(self, token_mint: str, wallet: Optional[str] = None, limit: int = 100) -> Sequence[HolderSnapshot]:
        stmt = select(HolderSnapshot).where(HolderSnapshot.token_mint == token_mint)
        if wallet:
            stmt = stmt.where(HolderSnapshot.wallet_address == wallet)
        result = await self.session.execute(
            stmt.order_by(HolderSnapshot.snapshot_at.desc()).limit(limit)
        )
        return result.scalars().all()
