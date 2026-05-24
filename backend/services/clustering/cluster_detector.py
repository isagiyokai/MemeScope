import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional, Sequence, Any
from collections import defaultdict

from sqlalchemy.ext.asyncio import AsyncSession

from models.trade import Trade
from models.wallet import Wallet
from repositories.trade_repo import TradeRepository
from repositories.wallet_repo import WalletRepository
from repositories.cluster_repo import ClusterRepository
from schemas.cluster_schema import ClusterCreate
from config.logging import get_logger
from config.constants import MIN_CLUSTER_SIZE, CLUSTER_SIMILARITY_THRESHOLD

logger = get_logger(__name__)


def _wallet_similarity(a: Sequence[Trade], b: Sequence[Trade]) -> float:
    """
    Compute a similarity score between two wallets based on token overlap,
    side alignment, and timing correlation.
    Returns a float 0.0-1.0.
    """
    if not a or not b:
        return 0.0

    # Token overlap
    tokens_a = {t.token_mint for t in a}
    tokens_b = {t.token_mint for t in b}
    if not tokens_a or not tokens_b:
        return 0.0

    overlap = len(tokens_a & tokens_b)
    union = len(tokens_a | tokens_b)
    token_score = overlap / union if union > 0 else 0.0

    # Side alignment on overlapping tokens
    side_match = 0
    side_total = 0
    for token in tokens_a & tokens_b:
        sides_a = {t.side.value if hasattr(t.side, "value") else t.side for t in a if t.token_mint == token}
        sides_b = {t.side.value if hasattr(t.side, "value") else t.side for t in b if t.token_mint == token}
        side_total += max(len(sides_a), len(sides_b))
        side_match += len(sides_a & sides_b)
    side_score = side_match / side_total if side_total > 0 else 0.0

    # Timing correlation (windowed hour buckets)
    def _hours(ts: datetime) -> int:
        return int(ts.timestamp() // 3600)

    hours_a = {_hours(t.timestamp) for t in a if t.timestamp}
    hours_b = {_hours(t.timestamp) for t in b if t.timestamp}
    if hours_a and hours_b:
        hour_overlap = len(hours_a & hours_b)
        hour_union = len(hours_a | hours_b)
        timing_score = hour_overlap / hour_union if hour_union > 0 else 0.0
    else:
        timing_score = 0.0

    # Weighted combination
    return token_score * 0.5 + side_score * 0.25 + timing_score * 0.25


class ClusterDetector:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.trade_repo = TradeRepository(session)
        self.wallet_repo = WalletRepository(session)
        self.cluster_repo = ClusterRepository(session)

    async def _get_recent_trades(self, cutoff: Optional[datetime] = None, limit_per_wallet: int = 200) -> dict[str, list[Trade]]:
        if cutoff is None:
            cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        # Fetch recent trades broadly (we will filter per wallet)
        # For performance, pull a recent window from DB ordered by timestamp
        stmt = (
            select(Trade)
            .where(Trade.timestamp >= cutoff)
            .order_by(Trade.timestamp.desc())
            .limit(5000)
        )
        from sqlalchemy import select
        result = await self.session.execute(stmt)
        trades: Sequence[Trade] = result.scalars().all()
        wallet_trades: dict[str, list[Trade]] = defaultdict(list)
        for t in trades:
            wallet_trades[t.wallet_address].append(t)
        return {w: ts[:limit_per_wallet] for w, ts in wallet_trades.items()}

    async def detect_clusters(
        self,
        min_size: int = MIN_CLUSTER_SIZE,
        similarity_threshold: float = CLUSTER_SIMILARITY_THRESHOLD,
        cutoff: Optional[datetime] = None,
    ) -> list[ClusterCreate]:
        wallet_trades = await self._get_recent_trades(cutoff=cutoff)
        wallets = list(wallet_trades.keys())
        n = len(wallets)
        if n < min_size:
            logger.info("Not enough wallets for clustering", wallets=n)
            return []

        # Build pairwise similarity matrix (upper triangle)
        edges: list[tuple[str, str, float]] = []
        for i in range(n):
            for j in range(i + 1, n):
                w1, w2 = wallets[i], wallets[j]
                sim = _wallet_similarity(wallet_trades[w1], wallet_trades[w2])
                if sim >= similarity_threshold:
                    edges.append((w1, w2, sim))

        # Union-find clustering on edges
        parent: dict[str, str] = {}

        def find(x: str) -> str:
            while parent.get(x, x) != x:
                parent[x] = parent.get(parent[x], parent[x])
                x = parent[x]
            return x

        def union(x: str, y: str):
            rx, ry = find(x), find(y)
            if rx != ry:
                parent[ry] = rx

        for w1, w2, _sim in edges:
            union(w1, w2)

        groups: dict[str, list[str]] = defaultdict(list)
        for w in wallets:
            groups[find(w)].append(w)

        clusters = []
        for root, members in groups.items():
            if len(members) < min_size:
                continue
            # Skip wallets already assigned to another cluster in DB (optional merge logic)
            cluster_id = root[:36]
            now = datetime.now(timezone.utc)
            clusters.append(ClusterCreate(
                cluster_id=cluster_id,
                wallets=",".join(members),
                wallet_count=len(members),
                common_funding_source=None,
                similarity_score=None,
                first_detected=now,
                last_updated=now,
                notes=f"Detected {len(members)} wallet cluster via trade overlap and timing",
            ))

        logger.info("Cluster detection complete", clusters=len(clusters), edges=len(edges))
        return clusters

    async def save_clusters(self, clusters: list[ClusterCreate]) -> list[Any]:
        saved = []
        for c in clusters:
            existing = await self.cluster_repo.get_by_cluster_id(c.cluster_id)
            if existing:
                # Merge wallets if new members found
                existing_wallets = set((existing.wallets or "").split(","))
                new_wallets = set(c.wallets.split(","))
                merged = existing_wallets | new_wallets
                await self.cluster_repo.update_cluster(
                    c.cluster_id,
                    wallets=",".join(sorted(merged)),
                    wallet_count=len(merged),
                    last_updated=datetime.now(timezone.utc),
                    notes=(existing.notes or "") + " | Updated with new detections",
                )
                saved.append(await self.cluster_repo.get_by_cluster_id(c.cluster_id))
            else:
                saved.append(await self.cluster_repo.create(c))
        return saved

    async def assign_cluster_tags(self, cluster_id: str) -> None:
        cluster = await self.cluster_repo.get_by_cluster_id(cluster_id)
        if not cluster:
            return
        wallets = [w.strip() for w in (cluster.wallets or "").split(",") if w.strip()]
        for addr in wallets:
            wallet = await self.wallet_repo.get_by_address(addr)
            if wallet:
                await self.wallet_repo.update_scores(
                    addr,
                    cluster_id=cluster_id,
                    tags=(wallet.tags or "") + ",clustered",
                )

    async def run(self) -> list[Any]:
        clusters = await self.detect_clusters()
        saved = await self.save_clusters(clusters)
        for c in saved:
            if c:
                await self.assign_cluster_tags(c.cluster_id)
        return saved
