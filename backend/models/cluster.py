import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Float, DateTime, Integer, Index
from sqlalchemy.dialects.postgresql import UUID

from core.db import Base


class Cluster(Base):
    __tablename__ = "clusters"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cluster_id = Column(String(36), unique=True, nullable=False, index=True)
    wallets = Column(String(2000), nullable=False)  # comma-separated wallet addresses
    wallet_count = Column(Integer, default=0)
    common_funding_source = Column(String(44), nullable=True)
    similarity_score = Column(Float, nullable=True)
    first_detected = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_updated = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    notes = Column(String(1000), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_clusters_wallet_count", "wallet_count"),
    )
