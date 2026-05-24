from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_db
from schemas.token_schema import TokenCreate, TokenRead, TokenList
from repositories.token_repo import TokenRepository
from config.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("", response_model=TokenList)
async def list_tokens(
    tracking: Optional[bool] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    repo = TokenRepository(db)
    items = await repo.list_tracking(limit=limit, offset=offset) if tracking is not False else []
    # For non-tracking or mixed, we could add a general list method later
    total = len(items)
    return TokenList(items=[TokenRead.model_validate(t) for t in items], total=total)


@router.get("/{mint}", response_model=TokenRead)
async def get_token(mint: str, db: AsyncSession = Depends(get_db)):
    repo = TokenRepository(db)
    token = await repo.get_by_mint(mint)
    if not token:
        raise HTTPException(status_code=404, detail="Token not found")
    return TokenRead.model_validate(token)


@router.post("", response_model=TokenRead)
async def create_token(data: TokenCreate, db: AsyncSession = Depends(get_db)):
    repo = TokenRepository(db)
    existing = await repo.get_by_mint(data.mint_address)
    if existing:
        raise HTTPException(status_code=409, detail="Token already tracked")
    token = await repo.create(data)
    return TokenRead.model_validate(token)
