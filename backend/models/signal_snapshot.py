import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Integer, DateTime, Index, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID, JSONB

from core.db import Base


class SignalSnapshot(Base):
    __tablename__ = "signal_snapshots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    signal_id = Column(UUID(as_uuid=True), ForeignKey("signals.id", ondelete="CASCADE"), nullable=False)
    token_mint = Column(String(44), nullable=False)

    # Market context captured at signal fire time
    fired_price_usd = Column(Numeric(20, 10), nullable=True)
    market_cap_usd = Column(Numeric(20, 2), nullable=True)
    liquidity_usd = Column(Numeric(20, 2), nullable=True)
    volume_1h_usd = Column(Numeric(20, 2), nullable=True)
    holders_count = Column(Integer, nullable=True)

    # Intelligence context
    smart_wallet_count = Column(Integer, nullable=True)
    avg_wallet_score = Column(Numeric(10, 4), nullable=True)
    triggering_wallets = Column(JSONB, nullable=True)  # [{address, score}]

    # Which rule version generated this signal
    signal_rule_version = Column(String(200), nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_signal_snapshots_signal_id", "signal_id"),
        Index("ix_signal_snapshots_token_mint", "token_mint"),
        Index("ix_signal_snapshots_created_at", "created_at"),
    )
