import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Float, DateTime, Integer, Index, ForeignKey
from sqlalchemy.dialects.postgresql import UUID

from core.db import Base


class HolderSnapshot(Base):
    __tablename__ = "holder_snapshots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    token_mint = Column(String(44), nullable=False, index=True)
    wallet_address = Column(String(44), nullable=False, index=True)
    rank = Column(Integer, nullable=False)
    balance = Column(Float, nullable=False)
    pct_supply = Column(Float, nullable=False)
    change_24h = Column(Float, nullable=True)
    change_7d = Column(Float, nullable=True)
    snapshot_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_holder_snapshots_token_rank", "token_mint", "rank"),
        Index("ix_holder_snapshots_token_wallet", "token_mint", "wallet_address"),
        Index("ix_holder_snapshots_snapshot_at", "snapshot_at"),
    )
