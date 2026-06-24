from datetime import datetime, timezone
from typing import Optional, Any

from config.constants import WSOL_MINT, TOKEN_PROGRAM
from config.logging import get_logger
from services.parser.swap_decoder import decode_swap, determine_program
from services.parser.transfer_parser import parse_spl_transfer, is_swap

logger = get_logger(__name__)


def normalize_event(tx: dict, signature: str, slot: Optional[int] = None) -> Optional[dict]:
    # PumpAPI WebSocket trade events arrive pre-structured under _pumpapi key
    pumpapi = tx.get("_pumpapi")
    if pumpapi:
        mint = pumpapi.get("mint")
        signer = (
            pumpapi.get("txSigner")
            or pumpapi.get("traderPublicKey")
            or pumpapi.get("trader")
            or pumpapi.get("user")
        )
        if not mint or not signer:
            return None
        sol_amount = float(pumpapi.get("solAmount", 0) or 0)
        token_amount = float(pumpapi.get("tokenAmount", 0) or 0)
        raw_tx_type = (pumpapi.get("txType") or pumpapi.get("type") or "").lower()
        if "isBuy" in pumpapi:
            is_buy = pumpapi["isBuy"]
        elif raw_tx_type == "buy":
            is_buy = True
        elif raw_tx_type == "sell":
            is_buy = False
        else:
            is_buy = True
        price = sol_amount / token_amount if token_amount > 0 else 0.0
        ts = pumpapi.get("timestamp")
        timestamp = datetime.fromtimestamp(ts, tz=timezone.utc) if ts else datetime.now(timezone.utc)
        return {
            "token_mint": mint,
            "wallet_address": signer,
            "side": "BUY" if is_buy else "SELL",
            "amount_token": token_amount,
            "amount_sol": sol_amount,
            "price_usd": price,
            "tx_signature": signature,
            "slot": slot,
            "program_id": "pumpfun",
            "is_parsed": 1,
            "timestamp": timestamp,
        }

    block_time = tx.get("blockTime")
    timestamp = datetime.fromtimestamp(block_time, tz=timezone.utc) if block_time else datetime.now(timezone.utc)

    if is_swap(tx):
        swap = decode_swap(tx)
        if not swap:
            return None

        # Determine wallet: fee payer or first signer
        msg = tx.get("transaction", {}).get("message", {})
        account_keys = msg.get("accountKeys", [])
        wallet = None
        for key in account_keys:
            if isinstance(key, dict):
                if key.get("signer"):
                    wallet = key.get("pubkey")
                    break
            elif isinstance(key, str):
                wallet = key
                break

        if not wallet:
            return None

        return {
            "token_mint": swap["token_mint"],
            "wallet_address": wallet,
            "side": swap["side"],
            "amount_token": swap["amount_token"],
            "amount_sol": swap.get("amount_sol", 0.0),
            "price_usd": swap.get("price", 0.0),
            "tx_signature": signature,
            "slot": slot,
            "program_id": swap.get("program", "unknown"),
            "is_parsed": 1,
            "timestamp": timestamp,
        }
    else:
        transfer = parse_spl_transfer(tx)
        if not transfer:
            return None

        msg = tx.get("transaction", {}).get("message", {})
        account_keys = msg.get("accountKeys", [])
        wallet = None
        for key in account_keys:
            if isinstance(key, dict):
                if key.get("signer"):
                    wallet = key.get("pubkey")
                    break
            elif isinstance(key, str):
                wallet = key
                break

        if not wallet:
            return None

        side = "TRANSFER_IN" if transfer["direction"] == "in" else "TRANSFER_OUT"

        return {
            "token_mint": transfer["token_mint"],
            "wallet_address": wallet,
            "side": side,
            "amount_token": transfer["amount_token"],
            "amount_sol": 0.0,
            "price_usd": 0.0,
            "tx_signature": signature,
            "slot": slot,
            "program_id": transfer.get("program", "spl_transfer"),
            "is_parsed": 0,
            "timestamp": timestamp,
        }
