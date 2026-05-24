import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone, timedelta

from services.signals.rules.smart_wallet_entry import SmartWalletEntryRule


def _trade(wallet, side="BUY", ts=None):
    t = MagicMock()
    t.wallet_address = wallet
    t.side = side
    t.timestamp = ts or datetime.now(timezone.utc)
    return t


def _wallet(score):
    w = MagicMock()
    w.composite_score = score
    return w


def _rule(trades, wallet_scores: dict):
    rule = SmartWalletEntryRule(MagicMock())
    rule.trade_repo = AsyncMock()
    rule.trade_repo.list_by_token = AsyncMock(return_value=trades)
    rule.wallet_repo = AsyncMock()
    rule.wallet_repo.get_by_address = AsyncMock(
        side_effect=lambda addr: wallet_scores.get(addr)
    )
    return rule


@pytest.mark.asyncio
async def test_no_signal_when_no_high_score_wallets():
    """Wallets with score < 70 -> no signal."""
    trades = [_trade("w1"), _trade("w2"), _trade("w3")]
    scores = {"w1": _wallet(50), "w2": _wallet(60), "w3": _wallet(65)}
    result = await _rule(trades, scores).evaluate("MintFakeForTests1111111111111111111111111")
    assert result is None


@pytest.mark.asyncio
async def test_no_signal_when_only_2_high_score_wallets():
    """2 high-score wallets is below the threshold of 3."""
    trades = [_trade("w1"), _trade("w2")]
    scores = {"w1": _wallet(80), "w2": _wallet(90)}
    result = await _rule(trades, scores).evaluate("MintFakeForTests1111111111111111111111111")
    assert result is None


@pytest.mark.asyncio
async def test_signal_triggers_at_3_high_score_wallets():
    """3 unique wallets with score >= 70 -> BUY signal emitted."""
    trades = [_trade(f"w{i}") for i in range(3)]
    scores = {f"w{i}": _wallet(80) for i in range(3)}
    result = await _rule(trades, scores).evaluate("MintFakeForTests1111111111111111111111111")
    assert result is not None
    assert "buy" in str(result.signal_type).lower()
    assert result.source_rule == "smart_wallet_entry"


@pytest.mark.asyncio
async def test_confidence_scales_above_3_wallets():
    """5 wallets should yield confidence higher than the 3-wallet baseline (0.8)."""
    trades = [_trade(f"w{i}") for i in range(5)]
    scores = {f"w{i}": _wallet(85) for i in range(5)}
    result = await _rule(trades, scores).evaluate("MintFakeForTests1111111111111111111111111")
    assert result is not None
    assert result.confidence > 0.8


@pytest.mark.asyncio
async def test_old_buys_excluded_from_count():
    """Buys older than 2 hours must not count toward the trigger."""
    old = datetime.now(timezone.utc) - timedelta(hours=3)
    trades = [_trade(f"w{i}", ts=old) for i in range(5)]
    scores = {f"w{i}": _wallet(90) for i in range(5)}
    result = await _rule(trades, scores).evaluate("MintFakeForTests1111111111111111111111111")
    assert result is None


@pytest.mark.asyncio
async def test_sell_trades_not_counted():
    """Only BUY side trades count; SELL trades from high-score wallets don't trigger."""
    trades = [_trade(f"w{i}", side="SELL") for i in range(5)]
    scores = {f"w{i}": _wallet(90) for i in range(5)}
    result = await _rule(trades, scores).evaluate("MintFakeForTests1111111111111111111111111")
    assert result is None


@pytest.mark.asyncio
async def test_duplicate_wallet_counted_once():
    """Same wallet buying twice counts as 1 unique, not 2."""
    trades = [_trade("w1"), _trade("w1"), _trade("w2"), _trade("w2")]
    scores = {"w1": _wallet(80), "w2": _wallet(80)}
    result = await _rule(trades, scores).evaluate("MintFakeForTests1111111111111111111111111")
    assert result is None  # only 2 unique, below threshold
