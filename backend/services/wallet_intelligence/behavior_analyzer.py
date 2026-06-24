from datetime import datetime, timezone
from typing import Optional, Sequence
from statistics import stdev, mean

from sqlalchemy.ext.asyncio import AsyncSession

from repositories.trade_repo import TradeRepository
from services import metrics
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
        """
        Score based on relative buy rank per token.
        Wallet that bought earliest among all observed buyers scores highest.
        Rank 1 of N → 100. Last buyer → 0. Averaged across all tokens bought.
        """
        tokens = await self.trade_repo.get_wallet_tokens(address)
        scores = []
        for token in tokens:
            wallet_trades = await self.trade_repo.list_by_wallet_token(address, token)
            first_buy = next(
                (t for t in sorted(wallet_trades, key=lambda t: t.timestamp) if t.side == "BUY"),
                None,
            )
            if not first_buy:
                continue
            all_buys = await self.trade_repo.list_by_token(token, limit=1000)
            all_buys_sorted = sorted(
                [t for t in all_buys if t.side == "BUY"],
                key=lambda t: t.timestamp,
            )
            if not all_buys_sorted:
                continue
            rank = next(
                (i + 1 for i, t in enumerate(all_buys_sorted) if t.id == first_buy.id),
                None,
            )
            if rank is None:
                continue
            total = len(all_buys_sorted)
            score = max(0.0, 100.0 * (1.0 - (rank - 1) / max(total, 1)))
            scores.append(score)
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

        # Build score from whichever components are available.
        # Weights are renormalized so missing components don't penalize the score.
        component_map: dict[str, tuple[Optional[float], float]] = {
            "win_rate":    (win_rate * 100 if win_rate is not None else None,  WINRATE_WEIGHT),
            "avg_roi":     (
                max(0, min(100, (avg_roi + 1.0) * 50)) if avg_roi is not None else None,
                ROI_WEIGHT,
            ),
            "timing":      (timing,      TIMING_WEIGHT),
            "consistency": (consistency, CONSISTENCY_WEIGHT),
        }

        available = {k: (v, w) for k, (v, w) in component_map.items() if v is not None}
        missing   = [k for k, (v, _) in component_map.items() if v is None]

        if not available:
            logger.debug("Wallet unscorable — no components available", wallet=address)
            metrics.increment("wallets_unscorable_total")
            return None

        total_weight = sum(w for _, w in available.values())
        score = sum(v * w / total_weight for v, w in available.values())
        score = round(score, 2)

        logger.debug(
            "Wallet scored",
            wallet=address,
            score=score,
            components_used=list(available.keys()),
            components_missing=missing,
        )
        metrics.increment("wallets_scored_total")

        return score
