import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_db
from schemas.signal_schema import SignalRead, SignalType
from schemas.signal_snapshot_schema import SignalSnapshotRead
from repositories.signal_repo import SignalRepository
from repositories.signal_snapshot_repo import SignalSnapshotRepository
from config.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("", response_model=list[SignalRead])
async def list_signals(
    signal_type: Optional[SignalType] = Query(None),
    min_confidence: Optional[float] = Query(None, ge=0.0, le=1.0),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    repo = SignalRepository(db)
    signals = await repo.list_recent(
        limit=limit, offset=offset, signal_type=signal_type, min_confidence=min_confidence
    )
    return [SignalRead.model_validate(s) for s in signals]


@router.get("/{signal_id}/snapshot", response_model=SignalSnapshotRead)
async def get_signal_snapshot(
    signal_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    repo = SignalSnapshotRepository(db)
    snapshot = await repo.get_by_signal(signal_id)
    if not snapshot:
        raise HTTPException(status_code=404, detail="Snapshot not found for this signal")
    return SignalSnapshotRead.model_validate(snapshot)


@router.get("/{token_mint}", response_model=list[SignalRead])
async def get_token_signals(
    token_mint: str,
    active_only: bool = Query(True),
    db: AsyncSession = Depends(get_db),
):
    repo = SignalRepository(db)
    signals = await repo.list_by_token(token_mint, active_only=active_only)
    return [SignalRead.model_validate(s) for s in signals]
