from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_db
from schemas.holder_schema import Top10HolderResponse, HolderSnapshotRead, HolderDiff
from repositories.holder_repo import HolderRepository
from repositories.token_repo import TokenRepository
from services.holders.holder_diff import HolderDiffEngine
from services.holders.top10_tracker import Top10Tracker
from clients.helius_client import HeliusClient
from config.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("/{token_mint}/top10", response_model=Top10HolderResponse)
async def get_top10(token_mint: str, db: AsyncSession = Depends(get_db)):
    repo = HolderRepository(db)
    holders = await repo.list_top10(token_mint)
    if not holders:
        raise HTTPException(status_code=404, detail="No holder data")
    token_repo = TokenRepository(db)
    token = await token_repo.get_by_mint(token_mint)
    total_supply = token.total_supply if token else None
    top10_pct = sum(h.pct_supply for h in holders) if holders else 0.0
    return Top10HolderResponse(
        token_mint=token_mint,
        holders=[HolderSnapshotRead.model_validate(h) for h in holders],
        total_supply=total_supply,
        top10_concentration=top10_pct,
        snapshot_at=holders[0].snapshot_at if holders else datetime.utcnow(),
    )


@router.get("/{token_mint}/history")
async def get_holder_history(
    token_mint: str,
    wallet: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    repo = HolderRepository(db)
    history = await repo.list_history(token_mint, wallet=wallet, limit=limit)
    return [HolderSnapshotRead.model_validate(h) for h in history]


@router.get("/{token_mint}/changes")
async def get_holder_changes(token_mint: str, db: AsyncSession = Depends(get_db)):
    engine = HolderDiffEngine(db)
    diffs = await engine.diff(token_mint)
    return diffs
