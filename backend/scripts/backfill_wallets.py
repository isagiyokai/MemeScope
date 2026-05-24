import asyncio
from datetime import datetime, timezone
from typing import Optional

from core.db import AsyncSessionLocal
from repositories.wallet_repo import WalletRepository
from services.wallet_intelligence.behavior_analyzer import BehaviorAnalyzer
from services.wallet_intelligence.winrate_calculator import WinRateCalculator
from services.wallet_intelligence.roi_engine import ROIEngine
from config.logging import configure_logging, get_logger

configure_logging()
logger = get_logger(__name__)


async def backfill_wallet_scores(wallet_addresses: Optional[list[str]] = None, batch_size: int = 50) -> None:
    async with AsyncSessionLocal() as session:
        wallet_repo = WalletRepository(session)
        if wallet_addresses:
            wallets = []
            for addr in wallet_addresses:
                w = await wallet_repo.get_by_address(addr)
                if w:
                    wallets.append(w)
        else:
            from sqlalchemy import select
            from models.wallet import Wallet as WalletModel
            result = await session.execute(select(WalletModel).limit(5000))
            wallets = result.scalars().all()

        analyzer = BehaviorAnalyzer(session)
        win_calc = WinRateCalculator(session)
        roi_calc = ROIEngine(session)

        total = len(wallets)
        updated = 0
        for i, wallet in enumerate(wallets):
            try:
                win_rate = await win_calc.calculate(wallet.address)
                avg_roi = await roi_calc.calculate_avg_roi(wallet.address)
                timing = await analyzer.entry_timing_score(wallet.address)
                consistency = await analyzer.consistency_score(wallet.address)
                composite = await analyzer.composite_score(
                    wallet.address,
                    win_rate=win_rate,
                    avg_roi=avg_roi,
                    timing=timing,
                    consistency=consistency,
                )
                await wallet_repo.update_scores(
                    wallet.address,
                    win_rate=win_rate,
                    avg_roi=avg_roi,
                    entry_timing_score=timing,
                    consistency_score=consistency,
                    composite_score=composite,
                    score_updated_at=datetime.now(timezone.utc),
                )
                updated += 1
                if (i + 1) % batch_size == 0:
                    logger.info('Backfill progress', processed=i + 1, total=total)
            except Exception as e:
                logger.error('Backfill failed for wallet', wallet=wallet.address, error=str(e))

        logger.info('Wallet backfill complete', updated=updated, total=total)


async def main():
    import sys
    if len(sys.argv) > 1:
        addresses = sys.argv[1:]
        await backfill_wallet_scores(wallet_addresses=addresses)
    else:
        await backfill_wallet_scores()


if __name__ == '__main__':
    asyncio.run(main())