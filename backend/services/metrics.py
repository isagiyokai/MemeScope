"""
Simple in-memory counters for signal pipeline observability.

Increment from anywhere; read via GET /metrics on the API.
Counters reset on process restart — intended for operational visibility, not persistence.
"""
import threading
from collections import defaultdict

_counters: dict[str, int] = defaultdict(int)
_lock = threading.Lock()


def increment(name: str, amount: int = 1) -> None:
    with _lock:
        _counters[name] += amount


def get_all() -> dict[str, int]:
    with _lock:
        return dict(_counters)


def reset(name: str) -> None:
    with _lock:
        _counters[name] = 0
