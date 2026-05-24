"""
Cluster funding source detection via Helius on-chain SOL transfer history.

Strategy: for each wallet in a cluster, fetch recent signatures around first_seen,
parse system-program Transfer instructions to find who funded the wallet with SOL.
If 2+ cluster wallets share a common funder -> that funder is the cluster's common_funding_source.
"""
from datetime import datetime, timezone, timedelta
from typing import Optional
from collections import defaultdict

from sqlalchemy.ext.asyncio import AsyncSession

from repositories.wallet_repo import WalletRepository
from repositories.cluster_repo import ClusterRepository
from config.logging import get_logger

logger = get_logger(__name__)

SYSTEM_PROGRAM = "11111111111111111111111111111111"
MAX_SIGS_PER_WALLET = 100  # limit Helius calls per wallet


def _extract_sol_senders(tx: dict, target_wallet: str) -> list[str]:
    """
    Return list of addresses that transferred SOL TO target_wallet in this tx.
    Uses parsed instructions from Helius getTransaction (encoding=jsonParsed).
    """
    senders = []
    msg = tx.get("transaction", {}).get("message", {})
    instructions = msg.get("instructions", [])
    inner = tx.get("meta", {}).get("innerInstructions", [])

    all_ixs = list(instructions)
    for inner_group in inner:
        all_ixs.extend(inner_group.get("instructions", []))

    for ix in all_ixs:
        if ix.get("program") != "system":
            continue
        parsed = ix.get("parsed", {})
        if not isinstance(parsed, dict):
            continue
        if parsed.get("type") != "transfer":
            continue
        info = parsed.get("info", {})
        dest = info.get("destination", "")
        src = info.get("source", "")
        lamports = info.get("lamports", 0)
        if dest == target_wallet and lamports > 0 and src:
            senders.append(src)

    return senders


class FundingTracker:
    """
    Detects common funding sources across cluster wallets using Helius RPC.
    Requires a HeliusClient to fetch on-chain SOL transfer history.
    """

    def __init__(self, session: AsyncSession, helius_client=None):
        self.session = session
        self.wallet_repo = WalletRepository(session)
        self._helius = helius_client

    def _get_helius(self):
        if self._helius is None:
            from clients.helius_client import HeliusClient
            self._helius = HeliusClient()
        return self._helius

    async def find_funding_candidates(
        self,
        wallets: list[str],
        window_hours: int = 48,
    ) -> dict[str, int]:
        """
        For each wallet, fetch SOL transfer history and collect funding sources.
        Returns map of {funder_address: count_of_wallets_funded}.
        """
        source_counts: dict[str, int] = defaultdict(int)
        helius = self._get_helius()

        for addr in wallets:
            wallet = await self.wallet_repo.get_by_address(addr)
            first_seen = wallet.first_seen if wallet else None

            try:
                sigs = await helius.get_signatures_for_address(addr, limit=MAX_SIGS_PER_WALLET)
            except Exception as e:
                logger.warning("Funding tracker: sig fetch failed", wallet=addr, error=str(e))
                continue

            seen_sources: set[str] = set()
            for entry in sigs:
                sig = entry.get("signature")
                if not sig:
                    continue

                # Filter by time window around first_seen if available
                block_time = entry.get("blockTime")
                if first_seen and block_time:
                    tx_time = datetime.fromtimestamp(block_time, tz=timezone.utc)
                    cutoff = first_seen + timedelta(hours=window_hours)
                    if tx_time > cutoff:
                        continue  # too recent; skip

                try:
                    tx = await helius.get_parsed_transaction(sig)
                except Exception as e:
                    logger.warning("Funding tracker: tx fetch failed", sig=sig, error=str(e))
                    continue

                if not tx:
                    continue

                senders = _extract_sol_senders(tx, addr)
                for s in senders:
                    if s != addr and s not in seen_sources:
                        seen_sources.add(s)

            for src in seen_sources:
                source_counts[src] += 1

        return dict(source_counts)

    async def assign_funding_to_cluster(self, cluster_id: str) -> Optional[str]:
        """
        Detect common funder for a cluster and persist it.
        Returns funder address if found, else None.
        """
        cluster_repo = ClusterRepository(self.session)
        cluster = await cluster_repo.get_by_cluster_id(cluster_id)
        if not cluster:
            return None

        wallets = [w.strip() for w in (cluster.wallets or "").split(",") if w.strip()]
        if len(wallets) < 2:
            return None

        funding_map = await self.find_funding_candidates(wallets)
        if not funding_map:
            return None

        # Require funder to appear for >= half of wallets (min 2)
        threshold = max(2, len(wallets) // 2)
        best = max(funding_map.items(), key=lambda x: x[1])
        if best[1] < threshold:
            return None

        await cluster_repo.update_cluster(
            cluster_id,
            common_funding_source=best[0],
            notes=(cluster.notes or "") + f" | Common funder: {best[0][:8]}... ({best[1]}/{len(wallets)} wallets)",
            last_updated=datetime.now(timezone.utc),
        )
        logger.info("Cluster funder assigned", cluster=cluster_id, funder=best[0][:8], matches=best[1])
        return best[0]

    async def run(self) -> dict[str, Optional[str]]:
        """Run funding detection across all clusters with >= 2 wallets."""
        cluster_repo = ClusterRepository(self.session)
        clusters = await cluster_repo.list_with_min_wallets(min_wallets=2)
        results = {}
        for c in clusters:
            source = await self.assign_funding_to_cluster(c.cluster_id)
            results[c.cluster_id] = source
        return results

    async def close(self):
        if self._helius:
            await self._helius.close()
