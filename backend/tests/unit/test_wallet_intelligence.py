import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from services.wallet_intelligence.behavior_analyzer import BehaviorAnalyzer
from services.wallet_intelligence.winrate_calculator import WinRateCalculator
from services.wallet_intelligence.roi_engine import ROIEngine


def _analyzer():
    return BehaviorAnalyzer(MagicMock())


@pytest.mark.asyncio
async def test_composite_score_within_range():
    """Mid-range inputs produce a score between 0 and 100."""
    score = await _analyzer().composite_score(
        "addr", win_rate=0.6, avg_roi=0.5, timing=80.0, consistency=70.0
    )
    assert score is not None
    assert 0.0 <= score <= 100.0


@pytest.mark.asyncio
async def test_composite_score_capped_at_100():
    """Extreme positive inputs must not exceed 100."""
    score = await _analyzer().composite_score(
        "addr", win_rate=1.0, avg_roi=10.0, timing=100.0, consistency=100.0
    )
    assert score is not None
    assert score <= 100.0


@pytest.mark.asyncio
async def test_composite_score_non_negative():
    """All-minimum inputs must produce score >= 0."""
    score = await _analyzer().composite_score(
        "addr", win_rate=0.0, avg_roi=-1.0, timing=0.0, consistency=0.0
    )
    assert score is not None
    assert score >= 0.0


@pytest.mark.asyncio
async def test_composite_score_returns_none_when_win_rate_missing():
    """composite_score returns None if any component (e.g. win_rate) can't be computed."""
    with patch.object(WinRateCalculator, "calculate", new=AsyncMock(return_value=None)), \
         patch.object(ROIEngine, "calculate_avg_roi", new=AsyncMock(return_value=None)):
        analyzer = _analyzer()
        analyzer.entry_timing_score = AsyncMock(return_value=None)
        analyzer.consistency_score = AsyncMock(return_value=None)
        score = await analyzer.composite_score("addr_with_no_trades")
    assert score is None


@pytest.mark.asyncio
async def test_composite_score_perfect_winrate_one():
    """100% win rate contributes correctly to final score."""
    score = await _analyzer().composite_score(
        "addr", win_rate=1.0, avg_roi=0.0, timing=50.0, consistency=50.0
    )
    assert score is not None
    # winrate=1.0 contributes 100*0.35=35; roi_norm=50*0.30=15; timing=50*0.20=10; cons=50*0.15=7.5 -> 67.5
    assert score == pytest.approx(67.5, abs=1.0)
