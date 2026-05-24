import pytest
from workers.parser_worker import process_raw_tx


@pytest.mark.asyncio
async def test_process_raw_tx_empty_payload_does_not_crash():
    """Empty payload is skipped gracefully (no signature -> early return)."""
    result = await process_raw_tx({"signature": "", "transaction": {}})
    assert result is None


@pytest.mark.asyncio
async def test_process_raw_tx_missing_transaction_key_does_not_crash():
    """Missing transaction key is handled without raising."""
    result = await process_raw_tx({})
    assert result is None


@pytest.mark.asyncio
async def test_process_raw_tx_no_parseable_event_does_not_crash():
    """A signature present but unparseable tx body is skipped cleanly."""
    raw = {
        "signature": "fakesig123",
        "slot": 999,
        "transaction": {
            "meta": {"preTokenBalances": [], "postTokenBalances": []},
            "transaction": {"message": {"accountKeys": [], "instructions": []}},
        },
    }
    result = await process_raw_tx(raw)
    assert result is None
