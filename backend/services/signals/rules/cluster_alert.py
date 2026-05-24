from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from schemas.signal_schema import SignalCreate, SignalType
from repositories.holder_repo import HolderRepository
from config.logging import get_logger
from config.constants import SIGNAL_CONFIDENCE_HIGH, SIGNAL_CONFIDENCE_MEDIUM

logger = get_logger(__name__)


class ClusterAlertRule:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.holder_repo = HolderRepository(session)

    async def evaluate(self, token_mint: str) -> Optional[SignalCreate]:
        top10 = await self.holder_repo.list_top10(token_mint)
        if not top10:
            return None

        cluster_pct = 0.0
        for h in top10:
            from sqlalchemy import text
            result = await self.session.execute(
                text("SELECT cluster_id FROM wallets WHERE address = :addr"),
                {"addr": h.wallet_address},
            )
            row = result.one_or_none()
            if row and row[0]:
                cluster_pct += h.pct_supply

        if cluster_pct >= 0.30:
            confidence = min(SIGNAL_CONFIDENCE_HIGH + (cluster_pct - 0.30) * 0.5, 0.98)
            return SignalCreate(
                token_mint=token_mint,
                signal_type=SignalType.ALERT,
                confidence=round(confidence, 2),
                reason=f"Detected cluster controlling {cluster_pct*100:.1f}% of supply in Top 10.",
                source_rule="cluster_alert",
                triggered_at=datetime.now(timezone.utc),
                is_active=True,
            )
        return None
