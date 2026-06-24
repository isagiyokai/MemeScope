from datetime import datetime, timezone, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from models.signal import Signal
from repositories.signal_snapshot_repo import SignalSnapshotRepository
from repositories.trade_repo import TradeRepository
from repositories.wallet_repo import WalletRepository
from config.constants import (
    SMART_WALLET_SCORE_THRESHOLD,
    SMART_WALLET_MIN_COUNT,
    SMART_WALLET_SCORE_THRESHOLD_COLD,
    SMART_WALLET_MIN_COUNT_COLD,
)
from config.logging import get_logger

logger = get_logger(__name__)


async def capture_signal_snapshot(session: AsyncSession, signal: Signal) -> None:
    """Capture full market and intelligence context at signal fire time. Never raises."""
    try:
        await _capture(session, signal)
    except Exception as e:
        logger.warning(
            "Signal snapshot capture failed — signal still created",
            signal_id=str(signal.id),
            token=signal.token_mint,
            error=str(e),
        )


async def _capture(session: AsyncSession, signal: Signal) -> None:
    from clients.birdeye_client import BirdeyeClient
    from config.settings import get_settings

    settings = get_settings()
    cold = settings.app.signal_cold_start_mode
    score_threshold = SMART_WALLET_SCORE_THRESHOLD_COLD if cold else SMART_WALLET_SCORE_THRESHOLD
    min_count = SMART_WALLET_MIN_COUNT_COLD if cold else SMART_WALLET_MIN_COUNT

    rule_version = (
        f"rule={signal.source_rule}"
        f",score>={score_threshold}"
        f",count>={min_count}"
        f",mode={'cold' if cold else 'production'}"
    )

    # 1. Birdeye market overview
    birdeye = BirdeyeClient()
    market: dict = {}
    try:
        market = await birdeye.get_token_overview(signal.token_mint) or {}
    except Exception as e:
        logger.warning("Birdeye overview unavailable for snapshot", token=signal.token_mint, error=str(e))
    finally:
        await birdeye.close()

    # 2. Triggering wallet context — mirrors SmartWalletEntryRule logic
    smart_wallet_count = None
    avg_wallet_score = None
    triggering_wallets = None
    try:
        trade_repo = TradeRepository(session)
        wallet_repo = WalletRepository(session)
        cutoff = datetime.now(timezone.utc) - timedelta(hours=2)
        trades = await trade_repo.list_by_token(signal.token_mint, limit=500)
        recent_buys = [
            t for t in trades
            if t.side == "BUY" and t.timestamp and t.timestamp >= cutoff
        ]
        qualified: dict[str, float] = {}
        for t in recent_buys:
            if t.wallet_address in qualified:
                continue
            wallet = await wallet_repo.get_by_address(t.wallet_address)
            if wallet and wallet.composite_score is not None and wallet.composite_score >= score_threshold:
                qualified[t.wallet_address] = float(wallet.composite_score)

        if qualified:
            smart_wallet_count = len(qualified)
            avg_wallet_score = sum(qualified.values()) / len(qualified)
            triggering_wallets = [
                {"address": addr, "score": score}
                for addr, score in qualified.items()
            ]
    except Exception as e:
        logger.warning("Wallet context unavailable for snapshot", token=signal.token_mint, error=str(e))

    # 3. Write snapshot — all market fields nullable, failure here would already be caught by outer handler
    repo = SignalSnapshotRepository(session)
    snapshot = await repo.create({
        "signal_id": signal.id,
        "token_mint": signal.token_mint,
        "fired_price_usd": market.get("price"),
        "market_cap_usd": market.get("market_cap"),
        "liquidity_usd": market.get("liquidity"),
        "volume_1h_usd": market.get("volume_1h"),
        "holders_count": market.get("holders_count"),
        "smart_wallet_count": smart_wallet_count,
        "avg_wallet_score": avg_wallet_score,
        "triggering_wallets": triggering_wallets,
        "signal_rule_version": rule_version,
    })
    logger.info(
        "Signal snapshot captured",
        signal_id=str(signal.id),
        token=signal.token_mint,
        price=market.get("price"),
        market_cap=market.get("market_cap"),
        smart_wallets=smart_wallet_count,
        rule_version=rule_version,
    )
