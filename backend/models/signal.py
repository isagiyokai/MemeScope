import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import Column, String, Float, DateTime, Integer, Index, Enum, Boolean
from sqlalchemy.dialects.postgresql import UUID

from core.db import Base


class SignalType(str, PyEnum):
    BUY = "BUY"
    WATCH = "WATCH"
    AVOID = "AVOID"
    ALERT = "ALERT"


class Signal(Base):
    __tablename__ = "signals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    token_mint = Column(String(44), nullable=False, index=True)
    signal_type = Column(Enum(SignalType), nullable=False)
    confidence = Column(Float, nullable=False)  # 0.0 - 1.0
    reason = Column(String(1000), nullable=False)
    source_rule = Column(String(100), nullable=False)
    historical_success_rate = Column(Float, nullable=True)
    triggered_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolution = Column(String(50), nullable=True)  # e.g. "confirmed", "expired", "false"
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_signals_token_active", "token_mint", "is_active"),
        Index("ix_signals_confidence", "confidence"),
        Index("ix_signals_triggered_at", "triggered_at"),
    )
