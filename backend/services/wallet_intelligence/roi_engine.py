from datetime import datetime, timezone
from typing import Sequence, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from repositories.trade_repo import TradeRepository
from config.logging import get_logger

logger = get_logger(__name__)


class ROIEngine:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.trade_repo = TradeRepository(session)

    async def calculate_avg_roi(self, address: str) -> Optional[float]:
        tokens = await self.trade_repo.get_wallet_tokens(address)
        rois = []
        for token in tokens:
            token_trades = await self.trade_repo.list_by_wallet_token(address, token)
            if not token_trades:
                continue
            buys = [t for t in token_trades if t.side == "BUY"]
            sells = [t for t in token_trades if t.side == "SELL"]
            total_buy = sum(t.value_usd or 0 for t in buys)
            total_sell = sum(t.value_usd or 0 for t in sells)
            if total_buy > 0:
                roi = (total_sell - total_buy) / total_buy
                rois.append(roi)

        if not rois:
            return None
        return round(sum(rois) / len(rois), 4)
