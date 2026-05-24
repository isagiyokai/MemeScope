from datetime import datetime, timezone, timedelta
from typing import Optional

import base58

from config.constants import is_valid_solana_address


def format_duration(seconds: float) -> str:
    if seconds < 60:
        return f"{int(seconds)}s"
    if seconds < 3600:
        return f"{int(seconds // 60)}m"
    if seconds < 86400:
        return f"{int(seconds // 3600)}h"
    return f"{int(seconds // 86400)}d"


def format_number(value: float, precision: int = 2) -> str:
    if value >= 1_000_000_000:
        return f"{value / 1_000_000_000:.{precision}f}B"
    if value >= 1_000_000:
        return f"{value / 1_000_000:.{precision}f}M"
    if value >= 1_000:
        return f"{value / 1_000:.{precision}f}K"
    return f"{value:.{precision}f}"


def format_percentage(value: float, precision: int = 2) -> str:
    return f"{value * 100:.{precision}f}%"


def truncate_address(address: str, chars: int = 4) -> str:
    if len(address) <= chars * 2 + 2:
        return address
    return f"{address[:chars]}...{address[-chars:]}"


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def hours_ago(hours: float) -> datetime:
    return now_utc() - timedelta(hours=hours)


def safe_divide(a: float, b: float, default: float = 0.0) -> float:
    return a / b if b != 0 else default
