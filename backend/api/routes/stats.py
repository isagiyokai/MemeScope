from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_db
from models.signal import Signal
from models.wallet import Wallet
from models.token import Token

router = APIRouter()


@router.get("")
async def get_stats(db: AsyncSession = Depends(get_db)):
    # active signals
    sig_result = await db.execute(
        select(func.count(), func.avg(Signal.confidence))
        .where(Signal.is_active == True)
    )
    sig_count, avg_conf = sig_result.one()

    # tracked wallets
    wallet_result = await db.execute(select(func.count()).select_from(Wallet))
    wallet_count = wallet_result.scalar_one()

    # tracked tokens
    token_result = await db.execute(select(func.count()).select_from(Token))
    token_count = token_result.scalar_one()

    return {
        "active_signals": sig_count or 0,
        "tracked_wallets": wallet_count or 0,
        "tokens_scanned": token_count or 0,
        "avg_confidence": round((avg_conf or 0) * 100, 1),
    }
