"""
Historical Helius backfill — fetch full on-chain trade history for tracked wallets.

Paginates getSignaturesForAddress (newest -> oldest) using the `before` cursor
until hitting the lookback limit or running out of signatures.

Run:
    PYTHONPATH=. python scripts/backfill_history.py [wallet1 wallet2 ...]
    PYTHONPATH=. python scripts/backfill_history.py --days 30
"""
import asyncio
import sys
import argparse
from datetime import datetime, timezone, timedelta

from core.db import AsyncSessionLocal
from clients.helius_client import HeliusClient
from services.parser.event_normalizer import normalize_event
from repositories.trade_repo import TradeRepository
from repositories.token_repo import TokenRepository
from repositories.wallet_repo import WalletRepository
from schemas.trade_schema import TradeCreate
from config.logging import configure_logging, get_logger

configure_logging()
logger = get_logger("backfill_history")

PAGE_SIZE = 100     # signatures per Helius call
MAX_PAGES = 20      # max pages per wallet (100 * 20 = 2000 txs)


async def backfill_wallet(
    address: str,
    helius: HeliusClient,
    cutoff: datetime,
) -> tuple[int, int]:
    """
    Fetch and store trades for one wallet.
    Returns (fetched_sigs, stored_trades).
    """
    async with AsyncSessionLocal() as session:
        trade_repo = TradeRepository(session)
        token_repo = TokenRepository(session)

        fetched = 0
        stored = 0
        before: str | None = None

        for page in range(MAX_PAGES):
            try:
                sigs = await helius.get_signatures_for_address(address, limit=PAGE_SIZE, before=before)
            except Exception as e:
                logger.error("Sig fetch failed", wallet=address, page=page, error=str(e))
                break

            if not sigs:
                break

            fetched += len(sigs)
            stop = False

            for entry in sigs:
                sig = entry.get("signature")
                block_time = entry.get("blockTime")

                if block_time:
                    tx_time = datetime.fromtimestamp(block_time, tz=timezone.utc)
                    if tx_time < cutoff:
                        stop = True
                        break

                if not sig:
                    continue

                # Skip if already stored
                existing = await trade_repo.get_by_signature(sig)
                if existing:
                    continue

                try:
                    tx = await helius.get_parsed_transaction(sig)
                except Exception as e:
                    logger.warning("Tx fetch failed", sig=sig, error=str(e))
                    continue

                if not tx:
                    continue

                event = normalize_event(tx, sig, entry.get("slot"))
                if not event:
                    continue

                # Ensure token exists (create minimal record if not)
                mint = event["token_mint"]
                if not await token_repo.get_by_mint(mint):
                    from schemas.token_schema import TokenCreate
                    try:
                        await token_repo.create(TokenCreate(
                            mint_address=mint,
                            name=mint[:8],
                            symbol="UNK",
                            decimals=6,
                            is_tracking=False,
                        ))
                    except Exception:
                        pass

                try:
                    await trade_repo.create(TradeCreate(**event))
                    stored += 1
                except Exception as e:
                    if "unique" not in str(e).lower() and "duplicate" not in str(e).lower():
                        logger.warning("Trade store failed", sig=sig, error=str(e))

            if stop or len(sigs) < PAGE_SIZE:
                break

            before = sigs[-1].get("signature")

        logger.info("Wallet backfill done", wallet=address[:8], fetched=fetched, stored=stored)
        return fetched, stored


async def main():
    parser = argparse.ArgumentParser(description="Backfill Helius trade history for wallets")
    parser.add_argument("wallets", nargs="*", help="Wallet addresses (default: all tracked wallets)")
    parser.add_argument("--days", type=int, default=30, help="How many days back to fetch (default: 30)")
    args = parser.parse_args()

    cutoff = datetime.now(timezone.utc) - timedelta(days=args.days)
    logger.info("Starting backfill", days=args.days, cutoff=cutoff.isoformat())

    if args.wallets:
        addresses = args.wallets
    else:
        async with AsyncSessionLocal() as session:
            repo = WalletRepository(session)
            wallets = await repo.list_all(limit=5000)
            addresses = [w.address for w in wallets]

    if not addresses:
        logger.info("No wallets to backfill")
        return

    helius = HeliusClient()
    total_fetched = 0
    total_stored = 0

    try:
        for i, addr in enumerate(addresses):
            logger.info("Backfilling wallet", index=i + 1, total=len(addresses), wallet=addr[:8])
            f, s = await backfill_wallet(addr, helius, cutoff)
            total_fetched += f
            total_stored += s
    finally:
        await helius.close()

    logger.info(
        "Backfill complete",
        wallets=len(addresses),
        total_fetched=total_fetched,
        total_stored=total_stored,
    )


if __name__ == "__main__":
    asyncio.run(main())
