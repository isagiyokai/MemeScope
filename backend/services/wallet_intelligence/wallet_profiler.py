from datetime import datetime, timezone
from typing import Optional, Sequence

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select

from models.trade import Trade
from models.wallet import Wallet
from schemas.wallet_schema import WalletProfile
from repositories.trade_repo import TradeRepository
from repositories.wallet_repo import WalletRepository
from config.logging import get_logger

logger = get_logger(__name__)


class WalletProfiler:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.trade_repo = TradeRepository(session)
        self.wallet_repo = WalletRepository(session)

    async def build_profile(self, address: str) -> Optional[WalletProfile]:
        wallet = await self.wallet_repo.get_by_address(address)
        if not wallet:
            return None

        trades = await self.trade_repo.list_by_wallet(address, limit=1000)
        total_trades = len(trades)
        total_volume = sum((t.value_usd or 0) for t in trades)
        avg_size = total_volume / total_trades if total_trades > 0 else 0.0
        tokens = await self.trade_repo.get_wallet_tokens(address)
        token_count = len(tokens)

        first_seen = min((t.timestamp for t in trades), default=wallet.first_seen or datetime.now(timezone.utc))
        last_active = max((t.timestamp for t in trades), default=wallet.last_active)

        # Categorize tokens into profitable / unprofitable
        profitable = 0
        unprofitable = 0
        for token in tokens:
            token_trades = [t for t in trades if t.token_mint == token]
            if not token_trades:
                continue
            token_trades.sort(key=lambda t: t.timestamp)
            buys = [t for t in token_trades if t.side == "BUY"]
            sells = [t for t in token_trades if t.side == "SELL"]
            total_buy = sum(t.value_usd or 0 for t in buys)
            total_sell = sum(t.value_usd or 0 for t in sells)
            if total_sell > total_buy * 1.1:
                profitable += 1
            elif total_sell < total_buy * 0.9:
                unprofitable += 1

        return WalletProfile(
            id=wallet.id,
            address=wallet.address,
            first_seen=first_seen,
            last_active=last_active,
            total_trades=total_trades,
            total_tokens_traded=token_count,
            total_volume_usd=total_volume,
            avg_trade_size_usd=avg_size,
            win_rate=wallet.win_rate,
            avg_roi=wallet.avg_roi,
            entry_timing_score=wallet.entry_timing_score,
            hold_duration_avg=wallet.hold_duration_avg,
            consistency_score=wallet.consistency_score,
            composite_score=wallet.composite_score,
            cluster_id=wallet.cluster_id,
            tags=wallet.tags,
            score_updated_at=wallet.score_updated_at,
            created_at=wallet.created_at,
            updated_at=wallet.updated_at,
            recent_trades=sum(1 for t in trades if t.timestamp and (datetime.now(timezone.utc) - t.timestamp).days <= 7),
            profitable_tokens=profitable,
            unprofitable_tokens=unprofitable,
        )
