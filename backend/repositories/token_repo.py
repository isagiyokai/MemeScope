from uuid import UUID
from typing import Optional, Sequence

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.token import Token
from schemas.token_schema import TokenCreate


class TokenRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, data: TokenCreate) -> Token:
        token = Token(**data.model_dump(exclude_unset=True))
        self.session.add(token)
        await self.session.commit()
        await self.session.refresh(token)
        return token

    async def get_by_mint(self, mint: str) -> Optional[Token]:
        result = await self.session.execute(select(Token).where(Token.mint_address == mint))
        return result.scalar_one_or_none()

    async def get_by_id(self, token_id: UUID) -> Optional[Token]:
        result = await self.session.execute(select(Token).where(Token.id == token_id))
        return result.scalar_one_or_none()

    async def list_tracking(self, limit: int = 500, offset: int = 0) -> Sequence[Token]:
        result = await self.session.execute(
            select(Token)
            .where(Token.is_tracking == True)
            .order_by(Token.updated_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()

    async def update_price(self, mint: str, price: float, price_change_24h: Optional[float] = None) -> Optional[Token]:
        await self.session.execute(
            update(Token)
            .where(Token.mint_address == mint)
            .values(current_price=price, price_change_24h=price_change_24h)
        )
        await self.session.commit()
        return await self.get_by_mint(mint)

    async def set_tracking(self, mint: str, tracking: bool = True) -> Optional[Token]:
        await self.session.execute(
            update(Token).where(Token.mint_address == mint).values(is_tracking=tracking)
        )
        await self.session.commit()
        return await self.get_by_mint(mint)
