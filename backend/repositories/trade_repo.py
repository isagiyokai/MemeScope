from uuid import UUID
from typing import Optional, Sequence
from datetime import datetime

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from models.trade import Trade, TradeSide
from schemas.trade_schema import TradeCreate


class TradeRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, data: TradeCreate) -> Trade:
        trade = Trade(**data.model_dump(exclude_unset=True))
        self.session.add(trade)
        await self.session.commit()
        await self.session.refresh(trade)
        return trade

    async def bulk_create(self, items: list[TradeCreate]) -> list[Trade]:
        trades = [Trade(**i.model_dump(exclude_unset=True)) for i in items]
        self.session.add_all(trades)
        await self.session.commit()
        for t in trades:
            await self.session.refresh(t)
        return trades

    async def get_by_signature(self, signature: str) -> Optional[Trade]:
        result = await self.session.execute(select(Trade).where(Trade.tx_signature == signature))
        return result.scalar_one_or_none()

    async def list_by_wallet(self, wallet: str, limit: int = 100, offset: int = 0) -> Sequence[Trade]:
        result = await self.session.execute(
            select(Trade)
            .where(Trade.wallet_address == wallet)
            .order_by(Trade.timestamp.desc())
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()

    async def list_by_token(self, token: str, limit: int = 100, offset: int = 0) -> Sequence[Trade]:
        result = await self.session.execute(
            select(Trade)
            .where(Trade.token_mint == token)
            .order_by(Trade.timestamp.desc())
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()

    async def list_by_wallet_token(self, wallet: str, token: str) -> Sequence[Trade]:
        result = await self.session.execute(
            select(Trade)
            .where(and_(Trade.wallet_address == wallet, Trade.token_mint == token))
            .order_by(Trade.timestamp.asc())
        )
        return result.scalars().all()

    async def count_by_wallet(self, wallet: str) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(Trade).where(Trade.wallet_address == wallet)
        )
        return result.scalar_one()

    async def get_wallet_tokens(self, wallet: str) -> Sequence[str]:
        result = await self.session.execute(
            select(Trade.token_mint)
            .where(Trade.wallet_address == wallet)
            .distinct()
        )
        return result.scalars().all()
