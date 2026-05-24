from datetime import datetime, timezone, timedelta
from typing import Optional, Sequence, Any
from collections import defaultdict

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.trade import Trade
from repositories.trade_repo import TradeRepository
from config.logging import get_logger

logger = get_logger(__name__)


class PatternMatcher:
    """
    Identifies wallets with correlated trading patterns beyond simple token overlap.
    Uses time-bucketed activity vectors and cosine similarity.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.trade_repo = TradeRepository(session)

    async def _build_activity_vectors(
        self,
        wallets: list[str],
        bucket_hours: int = 6,
        lookback_days: int = 7,
    ) -> dict[str, dict[str, int]]:
        """
        Build per-wallet activity vectors keyed by time bucket string: 'token:bucket'.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)
        vectors: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        for addr in wallets:
            trades = await self.trade_repo.list_by_wallet(addr, limit=500)
            for t in trades:
                if t.timestamp and t.timestamp >= cutoff:
                    bucket = self._bucket_key(t.timestamp, bucket_hours)
                    key = f"{t.token_mint}:{bucket}"
                    vectors[addr][key] += 1
        return dict(vectors)

    @staticmethod
    def _bucket_key(ts: datetime, bucket_hours: int) -> str:
        bucket = int(ts.timestamp() // (bucket_hours * 3600))
        return f"{bucket}"

    @staticmethod
    def _cosine_similarity(a: dict[str, int], b: dict[str, int]) -> float:
        keys = set(a.keys()) | set(b.keys())
        if not keys:
            return 0.0
        dot = sum(a.get(k, 0) * b.get(k, 0) for k in keys)
        norm_a = sum(v * v for v in a.values()) ** 0.5
        norm_b = sum(v * v for v in b.values()) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    async def find_correlated_pairs(
        self,
        wallets: list[str],
        threshold: float = 0.75,
    ) -> list[tuple[str, str, float]]:
        """Return wallet pairs with cosine similarity >= threshold."""
        vectors = await self._build_activity_vectors(wallets)
        pairs = []
        n = len(wallets)
        for i in range(n):
            for j in range(i + 1, n):
                w1, w2 = wallets[i], wallets[j]
                sim = self._cosine_similarity(vectors.get(w1, {}), vectors.get(w2, {}))
                if sim >= threshold:
                    pairs.append((w1, w2, round(sim, 4)))
        return pairs

    async def detect_pattern_clusters(self, wallets: list[str], threshold: float = 0.70) -> list[list[str]]:
        """
        Build connected components from correlated pairs.
        Returns groups of wallets that trade in similar patterns.
        """
        pairs = await self.find_correlated_pairs(wallets, threshold=threshold)
        parent: dict[str, str] = {w: w for w in wallets}

        def find(x: str) -> str:
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(x: str, y: str):
            rx, ry = find(x), find(y)
            if rx != ry:
                parent[ry] = rx

        for w1, w2, _sim in pairs:
            union(w1, w2)

        groups: dict[str, list[str]] = defaultdict(list)
        for w in wallets:
            groups[find(w)].append(w)

        clusters = [members for members in groups.values() if len(members) >= 2]
        logger.info("Pattern clusters detected", total=len(clusters), pairs=len(pairs))
        return clusters

    async def run(self, wallet_limit: int = 500) -> list[list[str]]:
        """Run pattern matching on recent active wallets."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        # Get wallets with recent trades
        stmt = select(Trade.wallet_address).distinct().where(Trade.timestamp >= cutoff)
        result = await self.session.execute(stmt)
        wallets = [r[0] for r in result.all() if r[0]]
        if not wallets:
            return []
        wallets = wallets[:wallet_limit]
        return await self.detect_pattern_clusters(wallets)
