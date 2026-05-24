import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class TradeSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    TRANSFER_IN = "TRANSFER_IN"
    TRANSFER_OUT = "TRANSFER_OUT"


class TradeBase(BaseModel):
    token_mint: str = Field(..., min_length=32, max_length=44)
    wallet_address: str = Field(..., min_length=32, max_length=44)
    side: TradeSide
    amount_token: float = Field(..., ge=0)
    amount_sol: Optional[float] = None
    price_usd: Optional[float] = None
    value_usd: Optional[float] = None
    tx_signature: str = Field(..., max_length=100)
    slot: Optional[int] = None
    program_id: Optional[str] = None
    is_parsed: int = 1
    timestamp: datetime


class TradeCreate(TradeBase):
    pass


class TradeRead(TradeBase):
    id: uuid.UUID
    created_at: datetime

    model_config = {"from_attributes": True}

