from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_db
from schemas.cluster_schema import ClusterRead
from repositories.cluster_repo import ClusterRepository
from services.clustering.cluster_detector import ClusterDetector
from config.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("", response_model=list[ClusterRead])
async def list_clusters(
    min_wallets: Optional[int] = Query(2, ge=2),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    repo = ClusterRepository(db)
    items = await repo.list_with_min_wallets(min_wallets=min_wallets, limit=limit)
    return [ClusterRead.model_validate(c) for c in items]


@router.get("/{cluster_id}", response_model=ClusterRead)
async def get_cluster(cluster_id: str, db: AsyncSession = Depends(get_db)):
    repo = ClusterRepository(db)
    cluster = await repo.get_by_cluster_id(cluster_id)
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")
    return ClusterRead.model_validate(cluster)


@router.post("/detect")
async def detect_clusters(db: AsyncSession = Depends(get_db)):
    detector = ClusterDetector(db)
    clusters = await detector.run()
    return {
        "detected": len(clusters),
        "cluster_ids": [c.cluster_id for c in clusters if hasattr(c, "cluster_id")],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/{cluster_id}/wallets")
async def get_cluster_wallets(cluster_id: str, db: AsyncSession = Depends(get_db)):
    repo = ClusterRepository(db)
    cluster = await repo.get_by_cluster_id(cluster_id)
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")
    wallets = [w.strip() for w in (cluster.wallets or "").split(",") if w.strip()]
    return {"cluster_id": cluster_id, "wallets": wallets}

