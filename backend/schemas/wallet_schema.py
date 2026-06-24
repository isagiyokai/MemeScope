import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class WalletBase(BaseModel):
    address: str = Field(..., min_length=32, max_length=44)
    first_seen: Optional[datetime] = None
    last_active: Optional[datetime] = None
    total_trades: int = 0
    total_tokens_traded: int = 0
    total_volume_usd: float = 0.0
    avg_trade_size_usd: float = 0.0
    win_rate: Optional[float] = None
    avg_roi: Optional[float] = None
    entry_timing_score: Optional[float] = None
    hold_duration_avg: Optional[float] = None
    consistency_score: Optional[float] = None
    composite_score: Optional[float] = 0.0
    cluster_id: Optional[str] = None
    tags: Optional[str] = None


class WalletCreate(WalletBase):
    pass


class WalletRead(WalletBase):
    id: uuid.UUID
    score_updated_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WalletProfile(WalletRead):
    recent_trades: int = 0
    profitable_tokens: int = 0
    unprofitable_tokens: int = 0
