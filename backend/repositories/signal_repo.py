from uuid import UUID
from typing import Optional, Sequence
from datetime import datetime

from sqlalchemy import select, and_, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.signal import Signal, SignalType
from schemas.signal_schema import SignalCreate


class SignalRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, data: SignalCreate) -> Signal:
        signal = Signal(**data.model_dump(exclude_unset=True))
        self.session.add(signal)
        await self.session.commit()
        await self.session.refresh(signal)
        return signal

    async def get_by_id(self, signal_id: UUID) -> Optional[Signal]:
        result = await self.session.execute(select(Signal).where(Signal.id == signal_id))
        return result.scalar_one_or_none()

    async def list_recent(self, limit: int = 100, offset: int = 0, signal_type: Optional[SignalType] = None, min_confidence: Optional[float] = None) -> Sequence[Signal]:
        stmt = select(Signal)
        if signal_type:
            stmt = stmt.where(Signal.signal_type == signal_type)
        if min_confidence is not None:
            stmt = stmt.where(Signal.confidence >= min_confidence)
        result = await self.session.execute(
            stmt.order_by(Signal.triggered_at.desc()).limit(limit).offset(offset)
        )
        return result.scalars().all()

    async def list_by_token(self, token_mint: str, active_only: bool = True) -> Sequence[Signal]:
        stmt = select(Signal).where(Signal.token_mint == token_mint)
        if active_only:
            stmt = stmt.where(Signal.is_active == True)
        result = await self.session.execute(
            stmt.order_by(Signal.triggered_at.desc()).limit(50)
        )
        return result.scalars().all()

    async def resolve(self, signal_id: UUID, resolution: str) -> Optional[Signal]:
        await self.session.execute(
            update(Signal)
            .where(Signal.id == signal_id)
            .values(resolution=resolution, is_active=False, resolved_at=datetime.utcnow())
        )
        await self.session.commit()
        return await self.get_by_id(signal_id)
