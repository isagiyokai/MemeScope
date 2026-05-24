import pytest
from services.parser.swap_decoder import decode_swap, determine_program
from services.parser.event_normalizer import normalize_event
from config.constants import (
    RAYDIUM_AMM_PROGRAM,
    JUPITER_AGGREGATOR_PROGRAM,
    PUMPFUN_PROGRAM,
    METEORA_DLMM_PROGRAM,
    ORCA_WHIRLPOOL_PROGRAM,
    WSOL_MINT,
)

TEST_MINT = "SomeFakeMint111111111111111111111111111111"
TEST_WALLET = "WalletFake111111111111111111111111111111111"


def _bal(amount):
    return {"uiTokenAmount": {"uiAmount": float(amount), "amount": str(int(float(amount) * 1_000_000))}}


def make_tx(program_id, pre_mints: dict, post_mints: dict, signer=TEST_WALLET):
    pre = [{"mint": m, **_bal(v)} for m, v in pre_mints.items()]
    post = [{"mint": m, **_bal(v)} for m, v in post_mints.items()]
    return {
        "transaction": {
            "message": {
                "accountKeys": [{"pubkey": signer, "signer": True, "writable": True}],
                "instructions": [{"programId": program_id}],
            }
        },
        "meta": {"preTokenBalances": pre, "postTokenBalances": post},
        "blockTime": 1700000000,
    }


# ─── determine_program ───────────────────────────────────────────────────────

def test_determine_program_raydium():
    tx = make_tx(RAYDIUM_AMM_PROGRAM, {TEST_MINT: 0, WSOL_MINT: 5}, {TEST_MINT: 1000, WSOL_MINT: 4})
    assert determine_program(tx) == "raydium"


def test_determine_program_pumpfun():
    tx = make_tx(PUMPFUN_PROGRAM, {TEST_MINT: 0}, {TEST_MINT: 500})
    assert determine_program(tx) == "pumpfun"


def test_determine_program_jupiter():
    tx = make_tx(JUPITER_AGGREGATOR_PROGRAM, {TEST_MINT: 0, WSOL_MINT: 2}, {TEST_MINT: 100, WSOL_MINT: 1.5})
    assert determine_program(tx) == "jupiter"


def test_determine_program_meteora():
    tx = make_tx(METEORA_DLMM_PROGRAM, {TEST_MINT: 0, WSOL_MINT: 2}, {TEST_MINT: 100, WSOL_MINT: 1.5})
    assert determine_program(tx) == "meteora"


def test_determine_program_orca():
    tx = make_tx(ORCA_WHIRLPOOL_PROGRAM, {TEST_MINT: 0, WSOL_MINT: 2}, {TEST_MINT: 100, WSOL_MINT: 1.5})
    assert determine_program(tx) == "orca"


def test_determine_program_unknown():
    tx = make_tx("UnknownProgram111111111111111111111111111", {TEST_MINT: 0}, {TEST_MINT: 100})
    assert determine_program(tx) == "unknown"


# ─── decode_swap ─────────────────────────────────────────────────────────────

def test_decode_raydium_swap_buy():
    tx = make_tx(RAYDIUM_AMM_PROGRAM,
                 {TEST_MINT: 0.0, WSOL_MINT: 5.0},
                 {TEST_MINT: 1000.0, WSOL_MINT: 4.5})
    result = decode_swap(tx)
    assert result is not None
    assert result["side"] == "BUY"
    assert result["token_mint"] == TEST_MINT
    assert result["amount_token"] == pytest.approx(1000.0)
    assert result["amount_sol"] == pytest.approx(0.5)


def test_decode_raydium_swap_sell():
    tx = make_tx(RAYDIUM_AMM_PROGRAM,
                 {TEST_MINT: 1000.0, WSOL_MINT: 4.5},
                 {TEST_MINT: 0.0, WSOL_MINT: 5.0})
    result = decode_swap(tx)
    assert result is not None
    assert result["side"] == "SELL"
    assert result["token_mint"] == TEST_MINT


def test_decode_swap_meteora_returns_correct_program():
    tx = make_tx(METEORA_DLMM_PROGRAM,
                 {TEST_MINT: 0.0, WSOL_MINT: 3.0},
                 {TEST_MINT: 500.0, WSOL_MINT: 2.5})
    result = decode_swap(tx)
    assert result is not None
    assert result["side"] == "BUY"
    assert result["program"] == "meteora"


def test_decode_swap_orca_returns_correct_program():
    tx = make_tx(ORCA_WHIRLPOOL_PROGRAM,
                 {TEST_MINT: 200.0, WSOL_MINT: 2.0},
                 {TEST_MINT: 0.0, WSOL_MINT: 2.8})
    result = decode_swap(tx)
    assert result is not None
    assert result["side"] == "SELL"
    assert result["program"] == "orca"


def test_decode_swap_empty_balances_returns_none():
    tx = make_tx(RAYDIUM_AMM_PROGRAM, {}, {})
    result = decode_swap(tx)
    assert result is None


def test_decode_swap_multi_account_same_mint_summed():
    """Multiple entries for same mint in balances must be summed, not overwritten."""
    tx = make_tx(RAYDIUM_AMM_PROGRAM, {}, {})
    # Inject duplicate mint entries directly
    tx["meta"]["preTokenBalances"] = [
        {"mint": TEST_MINT, **_bal(300)},
        {"mint": TEST_MINT, **_bal(200)},
        {"mint": WSOL_MINT, **_bal(5.0)},
    ]
    tx["meta"]["postTokenBalances"] = [
        {"mint": TEST_MINT, **_bal(200)},
        {"mint": TEST_MINT, **_bal(100)},
        {"mint": WSOL_MINT, **_bal(5.5)},
    ]
    result = decode_swap(tx)
    assert result is not None
    # pre total = 500, post total = 300 -> sold 200 tokens
    assert result["side"] == "SELL"
    assert result["amount_token"] == pytest.approx(200.0)


# ─── normalize_event / PumpAPI ───────────────────────────────────────────────

def test_normalize_event_pumpapi_buy():
    tx = {
        "_pumpapi": {
            "mint": TEST_MINT,
            "txSigner": TEST_WALLET,
            "solAmount": 1.5,
            "tokenAmount": 1000.0,
            "isBuy": True,
            "timestamp": 1700000000,
        }
    }
    result = normalize_event(tx, signature="testsig")
    assert result is not None
    assert result["side"] == "BUY"
    assert result["token_mint"] == TEST_MINT
    assert result["wallet_address"] == TEST_WALLET
    assert result["amount_sol"] == pytest.approx(1.5)
    assert result["program_id"] == "pumpfun"


def test_normalize_event_pumpapi_sell():
    tx = {
        "_pumpapi": {
            "mint": TEST_MINT,
            "txSigner": TEST_WALLET,
            "solAmount": 1.5,
            "tokenAmount": 1000.0,
            "isBuy": False,
            "timestamp": 1700000000,
        }
    }
    result = normalize_event(tx, signature="testsig")
    assert result is not None
    assert result["side"] == "SELL"


def test_normalize_event_pumpapi_missing_mint_returns_none():
    tx = {"_pumpapi": {"txSigner": TEST_WALLET, "solAmount": 1.0, "tokenAmount": 100.0}}
    result = normalize_event(tx, signature="nosig")
    assert result is None


def test_normalize_event_returns_none_on_empty_tx():
    result = normalize_event({}, signature="empty")
    assert result is None
