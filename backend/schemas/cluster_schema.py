import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ClusterBase(BaseModel):
    cluster_id: str = Field(..., max_length=36)
    wallets: str = Field(..., max_length=2000)
    wallet_count: int = 0
    common_funding_source: Optional[str] = None
    similarity_score: Optional[float] = None
    first_detected: datetime
    last_updated: datetime
    notes: Optional[str] = None


class ClusterCreate(ClusterBase):
    pass


class ClusterRead(ClusterBase):
    id: uuid.UUID
    created_at: datetime

    model_config = {"from_attributes": True}

