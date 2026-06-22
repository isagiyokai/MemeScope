import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Float, DateTime, Integer, Boolean, Index
from sqlalchemy.dialects.postgresql import UUID

from core.db import Base


class Token(Base):
    __tablename__ = "tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mint_address = Column(String(44), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=True)
    symbol = Column(String(50), nullable=True)
    decimals = Column(Integer, default=6)
    total_supply = Column(Float, nullable=True)
    circulating_supply = Column(Float, nullable=True)
    creator_wallet = Column(String(44), nullable=True, index=True)
    launch_platform = Column(String(50), nullable=True)  # e.g. pumpfun, raydium, jupiter
    launch_timestamp = Column(DateTime(timezone=True), nullable=True)
    current_price = Column(Float, nullable=True)
    price_change_24h = Column(Float, nullable=True)
    market_cap = Column(Float, nullable=True)
    liquidity_usd = Column(Float, nullable=True)
    volume_24h = Column(Float, nullable=True)
    holder_count = Column(Integer, nullable=True)
    is_tracking = Column(Boolean, default=True)
    last_trade_sig = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_tokens_is_tracking", "is_tracking"),
        Index("ix_tokens_launch_timestamp", "launch_timestamp"),
    )
