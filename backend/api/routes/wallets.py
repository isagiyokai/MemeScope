from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_db
from schemas.wallet_schema import WalletRead, WalletProfile
from schemas.trade_schema import TradeRead
from repositories.wallet_repo import WalletRepository
from repositories.trade_repo import TradeRepository
from services.wallet_intelligence.wallet_profiler import WalletProfiler
from config.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("/{address}", response_model=WalletProfile)
async def get_wallet(address: str, db: AsyncSession = Depends(get_db)):
    profiler = WalletProfiler(db)
    profile = await profiler.build_profile(address)
    if not profile:
        raise HTTPException(status_code=404, detail="Wallet not found")
    return profile


@router.get("/{address}/trades", response_model=list[TradeRead])
async def list_wallet_trades(
    address: str,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    repo = TradeRepository(db)
    trades = await repo.list_by_wallet(address, limit=limit, offset=offset)
    return [TradeRead.model_validate(t) for t in trades]


@router.get("/{address}/tokens")
async def list_wallet_tokens(address: str, db: AsyncSession = Depends(get_db)):
    repo = TradeRepository(db)
    tokens = await repo.get_wallet_tokens(address)
    return {"tokens": tokens, "count": len(tokens)}
