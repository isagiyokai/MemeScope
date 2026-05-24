import uuid
from typing import Optional, Sequence

from sqlalchemy import select, update, and_
from sqlalchemy.ext.asyncio import AsyncSession

from models.cluster import Cluster
from schemas.cluster_schema import ClusterCreate


class ClusterRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, data: ClusterCreate) -> Cluster:
        cluster = Cluster(**data.model_dump(exclude_unset=True))
        self.session.add(cluster)
        await self.session.commit()
        await self.session.refresh(cluster)
        return cluster

    async def get_by_cluster_id(self, cluster_id: str) -> Optional[Cluster]:
        result = await self.session.execute(select(Cluster).where(Cluster.cluster_id == cluster_id))
        return result.scalar_one_or_none()

    async def list_all(self, limit: int = 500, offset: int = 0) -> Sequence[Cluster]:
        result = await self.session.execute(
            select(Cluster)
            .order_by(Cluster.last_updated.desc())
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()

    async def list_with_min_wallets(self, min_wallets: int = 2, limit: int = 500) -> Sequence[Cluster]:
        result = await self.session.execute(
            select(Cluster)
            .where(Cluster.wallet_count >= min_wallets)
            .order_by(Cluster.wallet_count.desc())
            .limit(limit)
        )
        return result.scalars().all()

    async def update_cluster(self, cluster_id: str, **fields) -> Optional[Cluster]:
        await self.session.execute(
            update(Cluster)
            .where(Cluster.cluster_id == cluster_id)
            .values(**fields)
        )
        await self.session.commit()
        return await self.get_by_cluster_id(cluster_id)

    async def count(self) -> int:
        from sqlalchemy import func
        result = await self.session.execute(select(func.count()).select_from(Cluster))
        return result.scalar_one()
