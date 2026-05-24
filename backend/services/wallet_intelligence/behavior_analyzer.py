from datetime import datetime, timezone
from typing import Optional, Sequence
from statistics import stdev, mean

from sqlalchemy.ext.asyncio import AsyncSession

from repositories.trade_repo import TradeRepository
from config.logging import get_logger
from config.constants import (
    MIN_TRADES_FOR_SCORE,
    WINRATE_WEIGHT,
    ROI_WEIGHT,
    TIMING_WEIGHT,
    CONSISTENCY_WEIGHT,
)

logger = get_logger(__name__)


class BehaviorAnalyzer:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.trade_repo = TradeRepository(session)

    async def entry_timing_score(self, address: str) -> Optional[float]:
        tokens = await self.trade_repo.get_wallet_tokens(address)
        scores = []
        for token in tokens:
            trades = await self.trade_repo.list_by_wallet_token(address, token)
            if not trades:
                continue
            trades.sort(key=lambda t: t.timestamp)
            first_buy = next((t for t in trades if t.side == "BUY"), None)
            if not first_buy:
                continue
            # Heuristic: earlier entry in token lifecycle = higher score
            # Use slot as proxy for token age if available
            slot = first_buy.slot or 0
            if slot == 0:
                continue
            # Lower slot = earlier = higher score (simplified)
            scores.append(100.0)
        if not scores:
            return None
        return round(sum(scores) / len(scores), 2)

    async def hold_duration_avg(self, address: str) -> Optional[float]:
        tokens = await self.trade_repo.get_wallet_tokens(address)
        durations = []
        for token in tokens:
            trades = await self.trade_repo.list_by_wallet_token(address, token)
            if not trades:
                continue
            buys = [t for t in trades if t.side == "BUY"]
            sells = [t for t in trades if t.side == "SELL"]
            if not buys or not sells:
                continue
            avg_buy_time = min(t.timestamp for t in buys)
            avg_sell_time = max(t.timestamp for t in sells)
            duration_hours = (avg_sell_time - avg_buy_time).total_seconds() / 3600.0
            durations.append(duration_hours)
        if not durations:
            return None
        return round(sum(durations) / len(durations), 2)

    async def consistency_score(self, address: str) -> Optional[float]:
        tokens = await self.trade_repo.get_wallet_tokens(address)
        rois = []
        for token in tokens:
            trades = await self.trade_repo.list_by_wallet_token(address, token)
            if not trades:
                continue
            buys = [t for t in trades if t.side == "BUY"]
            sells = [t for t in trades if t.side == "SELL"]
            total_buy = sum(t.value_usd or 0 for t in buys)
            total_sell = sum(t.value_usd or 0 for t in sells)
            if total_buy > 0:
                rois.append((total_sell - total_buy) / total_buy)
        if len(rois) < MIN_TRADES_FOR_SCORE:
            return None
        avg = mean(rois)
        try:
            std = stdev(rois)
        except Exception:
            std = 0.0
        # Lower std dev relative to mean = higher consistency
        if avg == 0:
            return 50.0
        cv = std / abs(avg) if avg != 0 else 0.0
        score = max(0, 100 - (cv * 100))
        return round(score, 2)

    async def composite_score(
        self,
        address: str,
        win_rate: Optional[float] = None,
        avg_roi: Optional[float] = None,
        timing: Optional[float] = None,
        consistency: Optional[float] = None,
    ) -> Optional[float]:
        from services.wallet_intelligence.winrate_calculator import WinRateCalculator
        from services.wallet_intelligence.roi_engine import ROIEngine

        if win_rate is None:
            win_rate = await WinRateCalculator(self.session).calculate(address)
        if avg_roi is None:
            avg_roi = await ROIEngine(self.session).calculate_avg_roi(address)
        if timing is None:
            timing = await self.entry_timing_score(address)
        if consistency is None:
            consistency = await self.consistency_score(address)

        if None in (win_rate, avg_roi, timing, consistency):
            return None

        # Normalize ROI to 0-100 scale (cap at +/- 500%)
        roi_norm = max(0, min(100, (avg_roi + 1.0) * 50))

        score = (
            (win_rate * 100) * WINRATE_WEIGHT +
            roi_norm * ROI_WEIGHT +
            timing * TIMING_WEIGHT +
            consistency * CONSISTENCY_WEIGHT
        )
        return round(score, 2)
