from typing import Optional, Any
from datetime import datetime, timezone

from config.logging import get_logger

logger = get_logger(__name__)


def parse_spl_transfer(tx: dict) -> Optional[dict]:
    meta = tx.get("meta", {})
    pre = {b["mint"]: float(b.get("uiTokenAmount", {}).get("amount", 0)) for b in meta.get("preTokenBalances", []) if b}
    post = {b["mint"]: float(b.get("uiTokenAmount", {}).get("amount", 0)) for b in meta.get("postTokenBalances", []) if b}

    if not pre or not post:
        return None

    changes = {}
    for mint in set(pre.keys()) | set(post.keys()):
        changes[mint] = post.get(mint, 0) - pre.get(mint, 0)

    # Find the mint with largest absolute change
    target_mint = max(changes, key=lambda m: abs(changes[m]))
    amount = abs(changes[target_mint])
    if amount == 0:
        return None

    return {
        "token_mint": target_mint,
        "amount_token": amount,
        "direction": "in" if changes[target_mint] > 0 else "out",
        "program": "spl_transfer",
    }


def is_swap(tx: dict) -> bool:
    # Heuristic: if both WSOL and a non-WSOL token change, it is likely a swap
    meta = tx.get("meta", {})
    pre = {b["mint"]: float(b.get("uiTokenAmount", {}).get("amount", 0)) for b in meta.get("preTokenBalances", []) if b}
    post = {b["mint"]: float(b.get("uiTokenAmount", {}).get("amount", 0)) for b in meta.get("postTokenBalances", []) if b}

    if not pre or not post:
        return False

    sol_pre = pre.get("So11111111111111111111111111111111111111112", 0)
    sol_post = post.get("So11111111111111111111111111111111111111112", 0)
    sol_changed = abs(sol_post - sol_pre) > 0

    non_sol_changes = 0
    for mint in set(pre.keys()) | set(post.keys()):
        if mint == "So11111111111111111111111111111111111111112":
            continue
        if abs(post.get(mint, 0) - pre.get(mint, 0)) > 0:
            non_sol_changes += 1

    return sol_changed and non_sol_changes > 0
