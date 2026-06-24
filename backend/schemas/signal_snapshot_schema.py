import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class SignalSnapshotRead(BaseModel):
    id: uuid.UUID
    signal_id: uuid.UUID
    token_mint: str

    fired_price_usd: Optional[float] = None
    market_cap_usd: Optional[float] = None
    liquidity_usd: Optional[float] = None
    volume_1h_usd: Optional[float] = None
    holders_count: Optional[int] = None

    smart_wallet_count: Optional[int] = None
    avg_wallet_score: Optional[float] = None
    triggering_wallets: Optional[list[dict]] = None

    signal_rule_version: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}
