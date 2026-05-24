import asyncio
from datetime import datetime, timezone

from core.db import AsyncSessionLocal
from repositories.trade_repo import TradeRepository
from config.logging import configure_logging, get_logger

configure_logging()
logger = get_logger(__name__)


async def reprocess_unparsed_trades(limit: int = 500) -> int:
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select
        from models.trade import Trade
        stmt = (
            select(Trade)
            .where(Trade.is_parsed == 0)
            .order_by(Trade.timestamp.desc())
            .limit(limit)
        )
        result = await session.execute(stmt)
        trades = result.scalars().all()

        reprocessed = 0
        for trade in trades:
            try:
                trade.is_parsed = 1
                trade.timestamp = trade.timestamp or datetime.now(timezone.utc)
                await session.commit()
                reprocessed += 1
            except Exception as e:
                logger.error('Reprocess failed for trade', trade_id=str(trade.id), error=str(e))
                await session.rollback()

        logger.info('Reprocess complete', reprocessed=reprocessed, checked=len(trades))
        return reprocessed


async def main():
    import sys
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 500
    await reprocess_unparsed_trades(limit=limit)


if __name__ == '__main__':
    asyncio.run(main())