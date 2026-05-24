from collections import defaultdict
from typing import Optional

from config.constants import (
    RAYDIUM_AMM_PROGRAM,
    RAYDIUM_CLMM_PROGRAM,
    JUPITER_AGGREGATOR_PROGRAM,
    METEORA_DLMM_PROGRAM,
    ORCA_WHIRLPOOL_PROGRAM,
    PUMPFUN_PROGRAM,
    WSOL_MINT,
    TOKEN_PROGRAM,
)
from config.logging import get_logger

logger = get_logger(__name__)


def _token_balances(meta: dict, key: str) -> defaultdict:
    balances: defaultdict = defaultdict(float)
    for b in meta.get(key, []):
        if b:
            balances[b["mint"]] += float(b.get("uiTokenAmount", {}).get("uiAmount", 0) or 0)
    return balances


def decode_raydium_swap(tx: dict, token_mint: Optional[str] = None) -> Optional[dict]:
    meta = tx.get("meta", {})
    pre = _token_balances(meta, "preTokenBalances")
    post = _token_balances(meta, "postTokenBalances")

    if not pre or not post:
        return None

    mint_changes = {
        mint: post[mint] - pre[mint]
        for mint in set(pre) | set(post)
        if mint != WSOL_MINT
    }
    if not mint_changes:
        return None

    target_mint = max(mint_changes, key=lambda m: abs(mint_changes[m]))
    token_change = mint_changes[target_mint]
    sol_change = post[WSOL_MINT] - pre[WSOL_MINT]

    if token_change > 0 and sol_change < 0:
        side = "BUY"
    elif token_change < 0 and sol_change > 0:
        side = "SELL"
    else:
        side = "BUY" if token_change > 0 else "SELL"

    amount_token = abs(token_change)
    amount_sol = abs(sol_change)
    price = amount_sol / amount_token if amount_token > 0 else 0.0

    return {
        "token_mint": target_mint,
        "side": side,
        "amount_token": amount_token,
        "amount_sol": amount_sol,
        "price": price,
        "program": "raydium",
    }


def decode_jupiter_swap(tx: dict) -> Optional[dict]:
    meta = tx.get("meta", {})
    pre = _token_balances(meta, "preTokenBalances")
    post = _token_balances(meta, "postTokenBalances")

    if not pre or not post:
        return None

    mint_changes = {
        mint: post[mint] - pre[mint]
        for mint in set(pre) | set(post)
        if mint != WSOL_MINT
    }
    if not mint_changes:
        return None

    target_mint = max(mint_changes, key=lambda m: abs(mint_changes[m]))
    token_change = mint_changes[target_mint]
    sol_change = post[WSOL_MINT] - pre[WSOL_MINT]

    side = "BUY" if token_change > 0 else "SELL"
    amount_token = abs(token_change)
    amount_sol = abs(sol_change)
    price = amount_sol / amount_token if amount_token > 0 else 0.0

    return {
        "token_mint": target_mint,
        "side": side,
        "amount_token": amount_token,
        "amount_sol": amount_sol,
        "price": price,
        "program": "jupiter",
    }


def decode_pumpfun_swap(tx: dict) -> Optional[dict]:
    meta = tx.get("meta", {})
    pre = _token_balances(meta, "preTokenBalances")
    post = _token_balances(meta, "postTokenBalances")

    if not pre or not post:
        return None

    non_sol = [m for m in set(pre) | set(post) if m != WSOL_MINT]
    if not non_sol:
        return None

    target_mint = non_sol[0]
    token_change = post[target_mint] - pre[target_mint]
    sol_change = post[WSOL_MINT] - pre[WSOL_MINT]

    side = "BUY" if token_change > 0 else "SELL"
    amount_token = abs(token_change)
    amount_sol = abs(sol_change)
    price = amount_sol / amount_token if amount_token > 0 else 0.0

    return {
        "token_mint": target_mint,
        "side": side,
        "amount_token": amount_token,
        "amount_sol": amount_sol,
        "price": price,
        "program": "pumpfun",
    }


def determine_program(tx: dict) -> str:
    programs: set = set()
    account_keys = tx.get("transaction", {}).get("message", {}).get("accountKeys", [])
    for key in account_keys:
        owner = key.get("owner") if isinstance(key, dict) else None
        if owner:
            programs.add(owner)
    instructions = tx.get("transaction", {}).get("message", {}).get("instructions", [])
    for ix in instructions:
        prog = ix.get("programId") if isinstance(ix, dict) else None
        if prog:
            programs.add(prog)

    if PUMPFUN_PROGRAM in programs:
        return "pumpfun"
    if RAYDIUM_AMM_PROGRAM in programs or RAYDIUM_CLMM_PROGRAM in programs:
        return "raydium"
    if JUPITER_AGGREGATOR_PROGRAM in programs:
        return "jupiter"
    if METEORA_DLMM_PROGRAM in programs:
        return "meteora"
    if ORCA_WHIRLPOOL_PROGRAM in programs:
        return "orca"
    return "unknown"


def decode_swap(tx: dict) -> Optional[dict]:
    program = determine_program(tx)
    if program == "raydium":
        return decode_raydium_swap(tx)
    elif program == "jupiter":
        return decode_jupiter_swap(tx)
    elif program == "pumpfun":
        return decode_pumpfun_swap(tx)
    elif program in ("meteora", "orca"):
        result = decode_raydium_swap(tx)
        if result:
            result["program"] = program
        return result
    else:
        return decode_raydium_swap(tx)
