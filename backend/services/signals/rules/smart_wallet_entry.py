from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from schemas.signal_schema import SignalCreate, SignalType
from repositories.trade_repo import TradeRepository
from repositories.wallet_repo import WalletRepository
from config.logging import get_logger
from config.constants import SIGNAL_CONFIDENCE_HIGH, SIGNAL_CONFIDENCE_MEDIUM

logger = get_logger(__name__)


class SmartWalletEntryRule:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.trade_repo = TradeRepository(session)
        self.wallet_repo = WalletRepository(session)

    async def evaluate(self, token_mint: str) -> Optional[SignalCreate]:
        # Look for BUY trades in last 2 hours by high-score wallets
        cutoff = datetime.now(timezone.utc) - timedelta(hours=2)
        trades = await self.trade_repo.list_by_token(token_mint, limit=500)
        recent_buys = [t for t in trades if t.side == "BUY" and t.timestamp and t.timestamp >= cutoff]

        high_score_wallets = []
        for t in recent_buys:
            wallet = await self.wallet_repo.get_by_address(t.wallet_address)
            if wallet and wallet.composite_score and wallet.composite_score >= 70:
                high_score_wallets.append(t.wallet_address)

        unique_high_score = len(set(high_score_wallets))
        if unique_high_score >= 3:
            confidence = min(SIGNAL_CONFIDENCE_HIGH + (unique_high_score - 3) * 0.05, 0.98)
            return SignalCreate(
                token_mint=token_mint,
                signal_type=SignalType.BUY,
                confidence=round(confidence, 2),
                reason=f"{unique_high_score} high-quality wallets (score >=70) bought this token in the last 2 hours.",
                source_rule="smart_wallet_entry",
                triggered_at=datetime.now(timezone.utc),
                is_active=True,
            )
        return None
