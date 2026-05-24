import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from services.clustering.funding_tracker import FundingTracker, _extract_sol_senders


# ─── _extract_sol_senders unit tests ─────────────────────────────────────────

def _make_transfer_tx(source: str, destination: str, lamports: int) -> dict:
    return {
        "transaction": {
            "message": {
                "instructions": [
                    {
                        "program": "system",
                        "parsed": {
                            "type": "transfer",
                            "info": {"source": source, "destination": destination, "lamports": lamports},
                        },
                    }
                ]
            }
        },
        "meta": {"innerInstructions": []},
    }


def test_extract_sol_senders_finds_direct_transfer():
    tx = _make_transfer_tx("FUNDER111", "TARGET111", 1_000_000_000)
    result = _extract_sol_senders(tx, "TARGET111")
    assert "FUNDER111" in result


def test_extract_sol_senders_ignores_different_destination():
    tx = _make_transfer_tx("FUNDER111", "OTHER1111", 1_000_000_000)
    result = _extract_sol_senders(tx, "TARGET111")
    assert result == []


def test_extract_sol_senders_ignores_zero_lamports():
    tx = _make_transfer_tx("FUNDER111", "TARGET111", 0)
    result = _extract_sol_senders(tx, "TARGET111")
    assert result == []


def test_extract_sol_senders_finds_inner_instruction():
    tx = {
        "transaction": {"message": {"instructions": []}},
        "meta": {
            "innerInstructions": [
                {
                    "instructions": [
                        {
                            "program": "system",
                            "parsed": {
                                "type": "transfer",
                                "info": {"source": "INNER_SRC", "destination": "TARGET111", "lamports": 5000},
                            },
                        }
                    ]
                }
            ]
        },
    }
    result = _extract_sol_senders(tx, "TARGET111")
    assert "INNER_SRC" in result


def test_extract_sol_senders_skips_non_system_program():
    tx = {
        "transaction": {
            "message": {
                "instructions": [
                    {
                        "program": "token",
                        "parsed": {
                            "type": "transfer",
                            "info": {"source": "FUNDER111", "destination": "TARGET111", "lamports": 1000},
                        },
                    }
                ]
            }
        },
        "meta": {"innerInstructions": []},
    }
    result = _extract_sol_senders(tx, "TARGET111")
    assert result == []


# ─── FundingTracker.find_funding_candidates ───────────────────────────────────

def _tracker_with_mocks(sig_map: dict, tx_map: dict, wallet_map: dict = None):
    """
    sig_map: {wallet: [{"signature": "...", "blockTime": ...}, ...]}
    tx_map:  {sig: tx_dict}
    wallet_map: {addr: wallet_obj with first_seen}
    """
    session = MagicMock()
    helius = AsyncMock()
    helius.get_signatures_for_address = AsyncMock(side_effect=lambda addr, **kw: sig_map.get(addr, []))
    helius.get_parsed_transaction = AsyncMock(side_effect=lambda sig: tx_map.get(sig, {}))

    tracker = FundingTracker(session, helius_client=helius)
    tracker.wallet_repo = AsyncMock()
    tracker.wallet_repo.get_by_address = AsyncMock(
        side_effect=lambda addr: (wallet_map or {}).get(addr)
    )
    return tracker


async def test_find_funding_common_source_detected():
    """Two wallets funded by same source -> source count == 2."""
    funder = "CommonFunder11111111111111111111"
    w1, w2 = "Wallet1111111111111111111111111111", "Wallet2222222222222222222222222222"

    transfer_tx = _make_transfer_tx(funder, w1, 1_000_000_000)
    transfer_tx2 = _make_transfer_tx(funder, w2, 1_000_000_000)

    tracker = _tracker_with_mocks(
        sig_map={w1: [{"signature": "sig1"}], w2: [{"signature": "sig2"}]},
        tx_map={"sig1": transfer_tx, "sig2": transfer_tx2},
    )
    result = await tracker.find_funding_candidates([w1, w2])
    assert result.get(funder, 0) == 2


async def test_find_funding_no_common_source():
    """Different funders -> no entry with count >= 2."""
    w1, w2 = "Wallet1111111111111111111111111111", "Wallet2222222222222222222222222222"

    tracker = _tracker_with_mocks(
        sig_map={
            w1: [{"signature": "sig1"}],
            w2: [{"signature": "sig2"}],
        },
        tx_map={
            "sig1": _make_transfer_tx("Funder1111", w1, 1_000_000_000),
            "sig2": _make_transfer_tx("Funder2222", w2, 1_000_000_000),
        },
    )
    result = await tracker.find_funding_candidates([w1, w2])
    for count in result.values():
        assert count < 2


async def test_find_funding_handles_empty_wallet_list():
    tracker = _tracker_with_mocks({}, {})
    result = await tracker.find_funding_candidates([])
    assert result == {}


async def test_find_funding_helius_error_graceful():
    """Helius failure for one wallet doesn't crash; other wallets still processed."""
    w1, w2 = "Wallet1111111111111111111111111111", "Wallet2222222222222222222222222222"
    funder = "CommonFunder11111111111111111111"

    session = MagicMock()
    helius = AsyncMock()

    async def _sigs(addr, **kw):
        if addr == w1:
            raise Exception("connection error")
        return [{"signature": "sig2"}]

    helius.get_signatures_for_address = AsyncMock(side_effect=_sigs)
    helius.get_parsed_transaction = AsyncMock(return_value=_make_transfer_tx(funder, w2, 500_000_000))

    tracker = FundingTracker(session, helius_client=helius)
    tracker.wallet_repo = AsyncMock()
    tracker.wallet_repo.get_by_address = AsyncMock(return_value=None)

    result = await tracker.find_funding_candidates([w1, w2])
    # w2 processed successfully despite w1 failing
    assert funder in result
