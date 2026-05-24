from datetime import datetime, timezone, timedelta
from typing import Sequence, Optional, Any

from sqlalchemy.ext.asyncio import AsyncSession

from schemas.holder_schema import HolderDiff
from models.holder_snapshot import HolderSnapshot
from repositories.holder_repo import HolderRepository
from config.logging import get_logger

logger = get_logger(__name__)


class HolderDiffEngine:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = HolderRepository(session)

    async def diff(self, token_mint: str) -> list[HolderDiff]:
        # Get last two snapshots per wallet for this token
        history = await self.repo.list_history(token_mint, limit=200)
        if not history or len(history) < 2:
            return []

        # Group by wallet, take last 2
        wallet_snaps: dict[str, list[HolderSnapshot]] = {}
        for snap in history:
            wallet_snaps.setdefault(snap.wallet_address, []).append(snap)

        diffs = []
        for wallet, snaps in wallet_snaps.items():
            snaps_sorted = sorted(snaps, key=lambda s: s.snapshot_at, reverse=True)
            if len(snaps_sorted) < 2:
                continue
            latest = snaps_sorted[0]
            previous = snaps_sorted[1]

            rank_change = previous.rank - latest.rank  # positive = moved up
            balance_change = latest.balance - previous.balance
            pct_change = latest.pct_supply - previous.pct_supply

            if balance_change > 0:
                direction = "accumulation"
            elif balance_change < 0:
                direction = "distribution"
            else:
                direction = "stable"

            diffs.append(HolderDiff(
                wallet_address=wallet,
                rank_change=rank_change,
                balance_change=balance_change,
                pct_supply_change=pct_change,
                direction=direction,
            ))

        return diffs
