from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from schemas.signal_schema import SignalCreate, SignalType
from repositories.trade_repo import TradeRepository
from repositories.wallet_repo import WalletRepository
from services import metrics
from config.logging import get_logger
from config.constants import (
    SIGNAL_CONFIDENCE_HIGH,
    SMART_WALLET_SCORE_THRESHOLD,
    SMART_WALLET_MIN_COUNT,
    SMART_WALLET_SCORE_THRESHOLD_COLD,
    SMART_WALLET_MIN_COUNT_COLD,
)

logger = get_logger(__name__)


def _thresholds() -> tuple[float, int]:
    """Return (score_threshold, min_wallet_count) based on cold-start mode."""
    from config.settings import get_settings
    if get_settings().app.signal_cold_start_mode:
        return SMART_WALLET_SCORE_THRESHOLD_COLD, SMART_WALLET_MIN_COUNT_COLD
    return SMART_WALLET_SCORE_THRESHOLD, SMART_WALLET_MIN_COUNT


class SmartWalletEntryRule:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.trade_repo = TradeRepository(session)
        self.wallet_repo = WalletRepository(session)

    async def evaluate(self, token_mint: str) -> Optional[SignalCreate]:
        score_threshold, min_count = _thresholds()

        cutoff = datetime.now(timezone.utc) - timedelta(hours=2)
        trades = await self.trade_repo.list_by_token(token_mint, limit=500)
        recent_buys = [
            t for t in trades
            if t.side == "BUY" and t.timestamp and t.timestamp >= cutoff
        ]

        high_score_wallets = []
        for t in recent_buys:
            wallet = await self.wallet_repo.get_by_address(t.wallet_address)
            if wallet and wallet.composite_score is not None and wallet.composite_score >= score_threshold:
                high_score_wallets.append(t.wallet_address)

        unique_count = len(set(high_score_wallets))

        # Near-threshold logging and metrics
        if 0 < unique_count < min_count:
            logger.info(
                "Signal near threshold — smart_wallet_entry",
                token=token_mint,
                unique_smart_wallets=unique_count,
                required=min_count,
                score_threshold=score_threshold,
            )
            metrics.increment("signals_near_threshold_total")

        if unique_count >= min_count:
            confidence = min(SIGNAL_CONFIDENCE_HIGH + (unique_count - min_count) * 0.05, 0.98)
            logger.info(
                "SmartWalletEntry signal fired",
                token=token_mint,
                unique_smart_wallets=unique_count,
                score_threshold=score_threshold,
                cold_start=_thresholds() == (SMART_WALLET_SCORE_THRESHOLD_COLD, SMART_WALLET_MIN_COUNT_COLD),
            )
            return SignalCreate(
                token_mint=token_mint,
                signal_type=SignalType.BUY,
                confidence=round(confidence, 2),
                reason=(
                    f"{unique_count} wallets (score >={score_threshold}) "
                    f"bought in the last 2 hours."
                ),
                source_rule="smart_wallet_entry",
                triggered_at=datetime.now(timezone.utc),
                is_active=True,
            )
        return None
