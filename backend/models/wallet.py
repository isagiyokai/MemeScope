import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Float, DateTime, Integer, Index
from sqlalchemy.dialects.postgresql import UUID

from core.db import Base


class Wallet(Base):
    __tablename__ = "wallets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    address = Column(String(44), unique=True, nullable=False, index=True)
    first_seen = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_active = Column(DateTime(timezone=True), nullable=True)
    total_trades = Column(Integer, default=0)
    total_tokens_traded = Column(Integer, default=0)
    total_volume_usd = Column(Float, default=0.0)
    avg_trade_size_usd = Column(Float, default=0.0)
    win_rate = Column(Float, nullable=True)  # 0.0 - 1.0
    avg_roi = Column(Float, nullable=True)
    entry_timing_score = Column(Float, nullable=True)  # 0 - 100
    hold_duration_avg = Column(Float, nullable=True)  # hours
    consistency_score = Column(Float, nullable=True)  # 0 - 100
    composite_score = Column(Float, nullable=True)  # 0 - 100
    score_updated_at = Column(DateTime(timezone=True), nullable=True)
    cluster_id = Column(String(36), nullable=True)
    tags = Column(String(500), nullable=True)  # comma-separated labels
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_wallets_composite_score", "composite_score"),
        Index("ix_wallets_cluster_id", "cluster_id"),
    )
