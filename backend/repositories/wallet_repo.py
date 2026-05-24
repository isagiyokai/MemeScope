from uuid import UUID
from typing import Optional, Sequence

from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.wallet import Wallet
from schemas.wallet_schema import WalletCreate, WalletRead


class WalletRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, data: WalletCreate) -> Wallet:
        wallet = Wallet(**data.model_dump(exclude_unset=True))
        self.session.add(wallet)
        await self.session.commit()
        await self.session.refresh(wallet)
        return wallet

    async def get_by_address(self, address: str) -> Optional[Wallet]:
        result = await self.session.execute(select(Wallet).where(Wallet.address == address))
        return result.scalar_one_or_none()

    async def get_by_id(self, wallet_id: UUID) -> Optional[Wallet]:
        result = await self.session.execute(select(Wallet).where(Wallet.id == wallet_id))
        return result.scalar_one_or_none()

    async def list_high_score(self, min_score: float = 70.0, limit: int = 100) -> Sequence[Wallet]:
        result = await self.session.execute(
            select(Wallet)
            .where(Wallet.composite_score >= min_score)
            .order_by(Wallet.composite_score.desc())
            .limit(limit)
        )
        return result.scalars().all()

    async def update_scores(self, address: str, **fields) -> Optional[Wallet]:
        await self.session.execute(
            update(Wallet)
            .where(Wallet.address == address)
            .values(**fields)
        )
        await self.session.commit()
        return await self.get_by_address(address)

    async def list_all(self, limit: int = 5000) -> Sequence[Wallet]:
        result = await self.session.execute(select(Wallet).limit(limit))
        return result.scalars().all()

    async def count(self) -> int:
        result = await self.session.execute(select(func.count()).select_from(Wallet))
        return result.scalar_one()
