import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import Column, String, Float, DateTime, Integer, Index, Enum
from sqlalchemy.dialects.postgresql import UUID

from core.db import Base


class TradeSide(str, PyEnum):
    BUY = "BUY"
    SELL = "SELL"
    TRANSFER_IN = "TRANSFER_IN"
    TRANSFER_OUT = "TRANSFER_OUT"


class Trade(Base):
    __tablename__ = "trades"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    token_mint = Column(String(44), nullable=False, index=True)
    wallet_address = Column(String(44), nullable=False, index=True)
    side = Column(Enum(TradeSide), nullable=False)
    amount_token = Column(Float, nullable=False)
    amount_sol = Column(Float, nullable=True)
    price_usd = Column(Float, nullable=True)
    value_usd = Column(Float, nullable=True)
    tx_signature = Column(String(100), nullable=False, index=True)
    slot = Column(Integer, nullable=True)
    program_id = Column(String(44), nullable=True)  # which DEX/AMM
    is_parsed = Column(Integer, default=1)  # 1 = parsed swap, 0 = raw transfer
    timestamp = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_trades_token_wallet", "token_mint", "wallet_address"),
        Index("ix_trades_timestamp", "timestamp"),
        Index("ix_trades_slot", "slot"),
    )
