import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class SignalType(str, Enum):
    BUY = "BUY"
    WATCH = "WATCH"
    AVOID = "AVOID"
    ALERT = "ALERT"


class SignalBase(BaseModel):
    token_mint: str = Field(..., min_length=32, max_length=44)
    signal_type: SignalType
    confidence: float = Field(..., ge=0.0, le=1.0)
    reason: str = Field(..., max_length=1000)
    source_rule: str = Field(..., max_length=100)
    historical_success_rate: Optional[float] = None
    triggered_at: datetime
    expires_at: Optional[datetime] = None
    is_active: bool = True
    resolved_at: Optional[datetime] = None
    resolution: Optional[str] = None


class SignalCreate(SignalBase):
    pass


class SignalRead(SignalBase):
    id: uuid.UUID
    created_at: datetime

    model_config = {"from_attributes": True}
