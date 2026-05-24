import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class HolderSnapshotBase(BaseModel):
    token_mint: str = Field(..., min_length=32, max_length=44)
    wallet_address: str = Field(..., min_length=32, max_length=44)
    rank: int = Field(..., ge=1)
    balance: float = Field(..., ge=0)
    pct_supply: float = Field(..., ge=0, le=1)
    change_24h: Optional[float] = None
    change_7d: Optional[float] = None
    snapshot_at: datetime


class HolderSnapshotCreate(HolderSnapshotBase):
    pass


class HolderSnapshotRead(HolderSnapshotBase):
    id: uuid.UUID
    created_at: datetime

    model_config = {"from_attributes": True}


class Top10HolderResponse(BaseModel):
    token_mint: str
    holders: list[HolderSnapshotRead]
    total_supply: Optional[float] = None
    top10_concentration: Optional[float] = None
    snapshot_at: datetime


class HolderDiff(BaseModel):
    wallet_address: str
    rank_change: int = 0
    balance_change: float = 0.0
    pct_supply_change: float = 0.0
    direction: str = "stable"  # accumulation / distribution / stable / new / exited

