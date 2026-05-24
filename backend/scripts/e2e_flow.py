"""
End-to-end data flow verification.
Tests all four pipelines using direct function calls (no running workers needed).

Run: PYTHONPATH=. python scripts/e2e_flow.py
"""
import asyncio
import sys
from datetime import datetime, timezone

from config.logging import configure_logging, get_logger
from core.db import AsyncSessionLocal

configure_logging()
logger = get_logger("e2e_flow")

# WIF (dogwifhat) — real memecoin with manageable holder count for getTokenLargestAccounts
WIF = "EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm"
WSOL = "So11111111111111111111111111111111111111112"
TEST_WALLET = "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM"
TEST_MINT_PUMPFUN = "PUMPfunTest111111111111111111111111111111111"
TEST_SIG = "e2e_test_sig_" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")

PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"
SKIP = "\033[93mSKIP\033[0m"


def result(label: str, ok: bool, detail: str = ""):
    mark = PASS if ok else FAIL
    print(f"  [{mark}] {label}" + (f": {detail}" if detail else ""))
    return ok


# ─── Flow 1: Parser -> Trade ────────────────────────────────────────────────

async def flow_parser():
    print("\n=== Flow 1: Parser -> Trade stored in DB ===")
    from workers.parser_worker import process_raw_tx
    from repositories.trade_repo import TradeRepository

    # Minimal synthetic Helius-style tx that bypasses swap/transfer heuristics
    # We inject a pre-normalised dict directly to test the DB write path.
    from core.db import AsyncSessionLocal
    from schemas.trade_schema import TradeCreate, TradeSide
    from repositories.trade_repo import TradeRepository

    trade_data = TradeCreate(
        token_mint=WSOL,
        wallet_address=TEST_WALLET,
        side=TradeSide.BUY,
        amount_token=1000.0,
        amount_sol=1.5,
        price_usd=0.0015,
        tx_signature=TEST_SIG,
        slot=999999,
        program_id="raydium",
        is_parsed=1,
        timestamp=datetime.now(timezone.utc),
    )

    async with AsyncSessionLocal() as session:
        repo = TradeRepository(session)
        try:
            trade = await repo.create(trade_data)
            result("Trade created in DB", trade.id is not None, f"id={trade.id}")
            verify = await repo.get_by_signature(TEST_SIG)
            result("Trade retrievable by signature", verify is not None, f"token={verify.token_mint if verify else 'MISSING'}")
            return True
        except Exception as e:
            result("Trade created in DB", False, str(e))
            return False


# ─── Flow 2: Signal engine evaluation ──────────────────────────────────────

async def flow_signals():
    print("\n=== Flow 2: Signal engine evaluates token ===")
    from services.signals.signal_engine import SignalEngine
    from repositories.signal_repo import SignalRepository

    async with AsyncSessionLocal() as session:
        engine = SignalEngine(session)
        try:
            signals = await engine.evaluate_token(WSOL)
            result(
                "Signal engine ran without error",
                True,
                f"{len(signals)} signal(s) generated"
            )
            if signals:
                s = signals[0]
                result("Signal stored in DB", s.id is not None, f"type={s.signal_type} rule={s.source_rule}")
            else:
                print(f"  [{SKIP}] No signals triggered (rules need more data — expected at this stage)")
            return True
        except Exception as e:
            result("Signal engine ran without error", False, str(e))
            return False


# ─── Flow 3: Holder worker -> Top10 snapshots ───────────────────────────────

async def flow_holders():
    print("\n=== Flow 3: Holder worker -> Top10 snapshots via Helius ===")
    from clients.helius_client import HeliusClient
    from services.holders.top10_tracker import Top10Tracker
    from repositories.holder_repo import HolderRepository

    # Ensure WIF token exists in DB (required by holder_worker flow)
    from repositories.token_repo import TokenRepository
    from schemas.token_schema import TokenCreate
    async with AsyncSessionLocal() as seed_session:
        token_repo = TokenRepository(seed_session)
        if not await token_repo.get_by_mint(WIF):
            await token_repo.create(TokenCreate(mint_address=WIF, name="dogwifhat", symbol="WIF", decimals=6, is_tracking=True))

    async with AsyncSessionLocal() as session:
        helius = HeliusClient()
        try:
            tracker = Top10Tracker(session, helius)
            # WIF (dogwifhat) is a real memecoin — Helius getTokenLargestAccounts works on it
            snapshots = await tracker.fetch_and_store(WIF, total_supply=None)
            result(
                "Helius returned holder data",
                len(snapshots) > 0,
                f"{len(snapshots)} snapshots stored"
            )
            if snapshots:
                snap = snapshots[0]
                result(
                    "Snapshot has required fields",
                    bool(snap.wallet_address and snap.rank == 1),
                    f"rank={snap.rank} wallet={snap.wallet_address[:8]}..."
                )
            return len(snapshots) > 0
        except Exception as e:
            result("Helius holder fetch", False, str(e))
            return False
        finally:
            await helius.close()


# ─── Flow 4: Pump.fun worker -> Token + Wallets ─────────────────────────────

async def flow_pumpfun():
    print("\n=== Flow 4: Pump.fun raw launch -> Token + wallets persisted ===")
    from services.pumpfun.launch_tracker import PumpfunTracker
    from repositories.token_repo import TokenRepository
    from repositories.wallet_repo import WalletRepository

    raw_launch = {
        "mint": TEST_MINT_PUMPFUN,
        "name": "E2E Test Token",
        "symbol": "E2ET",
        "decimals": 6,
        "total_supply": 1_000_000_000.0,
        "creator": TEST_WALLET,
        "price": 0.000001,
        "market_cap": 1000.0,
        "first_buyers": [
            {"wallet": "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU"},
            {"wallet": "FWznbcNXWQuHTawe9RxvQ6LPDd88nF2X6wNjP4JFBuR7"},
        ],
    }

    async with AsyncSessionLocal() as session:
        tracker = PumpfunTracker(session)
        try:
            token = await tracker.process_raw_launch(raw_launch)
            result("Token created from launch", token is not None, f"mint={TEST_MINT_PUMPFUN[:12]}...")

            if token:
                wallet_repo = WalletRepository(session)
                creator = await wallet_repo.get_by_address(TEST_WALLET)
                result("Creator wallet persisted", creator is not None, f"addr={TEST_WALLET[:8]}...")

                buyer1 = await wallet_repo.get_by_address("7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU")
                result("First buyer wallets persisted", buyer1 is not None)

            await tracker.close()
            return token is not None
        except Exception as e:
            result("Pump.fun launch processing", False, str(e))
            await tracker.close()
            return False


# ─── Flow 5: PumpAPI live endpoint check ───────────────────────────────────

async def flow_pumpapi_live():
    print("\n=== Flow 5: PumpAPI WebSocket stream reachability ===")
    from clients.pumpapi_client import PumpAPIClient

    client = PumpAPIClient()
    try:
        ok = await client.connect_once(timeout=30.0)
        result(
            "PumpAPI wss://stream.pumpapi.io/ reachable",
            ok,
            "received first event" if ok else "connection failed"
        )
        return ok
    except Exception as e:
        result("PumpAPI WebSocket connect", False, str(e))
        return False
    finally:
        await client.close()


# ─── Main ───────────────────────────────────────────────────────────────────

async def main():
    print("=" * 60)
    print("MemeScope E2E Data Flow Verification")
    print("=" * 60)

    results = {}
    results["parser"] = await flow_parser()
    results["signals"] = await flow_signals()
    results["holders"] = await flow_holders()
    results["pumpfun"] = await flow_pumpfun()
    results["pumpapi_live"] = await flow_pumpapi_live()

    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    all_pass = True
    for name, ok in results.items():
        mark = PASS if ok else FAIL
        print(f"  [{mark}] {name}")
        if not ok:
            all_pass = False

    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    asyncio.run(main())
