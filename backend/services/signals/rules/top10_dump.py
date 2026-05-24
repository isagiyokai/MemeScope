from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from schemas.signal_schema import SignalCreate, SignalType
from repositories.holder_repo import HolderRepository
from config.logging import get_logger
from config.constants import HOLDER_DUMP_THRESHOLD_PCT, SIGNAL_CONFIDENCE_HIGH, SIGNAL_CONFIDENCE_MEDIUM

logger = get_logger(__name__)


class Top10DumpRule:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.holder_repo = HolderRepository(session)

    async def evaluate(self, token_mint: str) -> Optional[SignalCreate]:
        # Compare latest Top10 snapshot to previous to detect distribution
        from services.holders.holder_diff import HolderDiffEngine
        engine = HolderDiffEngine(self.session)
        diffs = await engine.diff(token_mint)
        if not diffs:
            return None

        total_pct_lost = sum(d.pct_supply_change for d in diffs if d.pct_supply_change < 0)
        if abs(total_pct_lost) >= HOLDER_DUMP_THRESHOLD_PCT:
            confidence = min(SIGNAL_CONFIDENCE_HIGH + abs(total_pct_lost) * 0.01, 0.98)
            return SignalCreate(
                token_mint=token_mint,
                signal_type=SignalType.AVOID,
                confidence=round(confidence, 2),
                reason=f"Top 10 holders dumped {abs(total_pct_lost):.2f}% of supply recently.",
                source_rule="top10_dump",
                triggered_at=datetime.now(timezone.utc),
                is_active=True,
            )
        return None
