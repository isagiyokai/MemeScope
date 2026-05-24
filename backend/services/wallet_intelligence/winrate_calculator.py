from datetime import datetime, timezone
from typing import Sequence, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from models.trade import Trade
from repositories.trade_repo import TradeRepository
from config.logging import get_logger
from config.constants import MIN_TRADES_FOR_SCORE

logger = get_logger(__name__)


class WinRateCalculator:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.trade_repo = TradeRepository(session)

    async def calculate(self, address: str) -> Optional[float]:
        tokens = await self.trade_repo.get_wallet_tokens(address)
        if len(tokens) < MIN_TRADES_FOR_SCORE:
            return None

        profitable = 0
        total = 0
        for token in tokens:
            token_trades = await self.trade_repo.list_by_wallet_token(address, token)
            if not token_trades:
                continue
            token_trades.sort(key=lambda t: t.timestamp)
            buys = [t for t in token_trades if t.side == "BUY"]
            sells = [t for t in token_trades if t.side == "SELL"]
            total_buy = sum(t.value_usd or 0 for t in buys)
            total_sell = sum(t.value_usd or 0 for t in sells)
            total += 1
            if total_sell > total_buy * 1.05:  # 5% profit threshold
                profitable += 1

        if total == 0:
            return None
        return round(profitable / total, 4)
