import uuid
from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.signal_snapshot import SignalSnapshot


class SignalSnapshotRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, data: dict) -> SignalSnapshot:
        snapshot = SignalSnapshot(**data)
        self.session.add(snapshot)
        await self.session.commit()
        await self.session.refresh(snapshot)
        return snapshot

    async def get_by_signal(self, signal_id: uuid.UUID) -> Optional[SignalSnapshot]:
        result = await self.session.execute(
            select(SignalSnapshot).where(SignalSnapshot.signal_id == signal_id)
        )
        return result.scalar_one_or_none()

    async def list_by_token(self, token_mint: str, limit: int = 50) -> Sequence[SignalSnapshot]:
        result = await self.session.execute(
            select(SignalSnapshot)
            .where(SignalSnapshot.token_mint == token_mint)
            .order_by(SignalSnapshot.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()
