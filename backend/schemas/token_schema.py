import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class TokenBase(BaseModel):
    mint_address: str = Field(..., min_length=32, max_length=44)
    name: Optional[str] = None
    symbol: Optional[str] = None
    decimals: int = 6
    total_supply: Optional[float] = None
    circulating_supply: Optional[float] = None
    creator_wallet: Optional[str] = None
    launch_platform: Optional[str] = None
    launch_timestamp: Optional[datetime] = None
    current_price: Optional[float] = None
    price_change_24h: Optional[float] = None
    market_cap: Optional[float] = None
    liquidity_usd: Optional[float] = None
    volume_24h: Optional[float] = None
    holder_count: Optional[int] = None
    is_tracking: bool = True


class TokenCreate(TokenBase):
    pass


class TokenRead(TokenBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TokenList(BaseModel):
    items: list[TokenRead]
    total: int
