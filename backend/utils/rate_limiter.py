import asyncio
import json
import time
from pathlib import Path
from typing import Optional

from config.logging import get_logger

logger = get_logger(__name__)

_STATE_FILE = Path(__file__).parent / ".rate_state.json"
_PROBE_INTERVAL_DAYS = 3
_PROBE_DURATION_HOURS = 24   # run probe for this long before committing
_PROBE_FACTOR = 0.10          # 10 % increase per probe cycle
_MAX_PROBE_ERRORS = 3         # 429s before aborting probe


class RateLimiter:
    """
    Async token-bucket rate limiter.
    Enforces minimum interval between requests; safe for concurrent callers via Lock.
    """

    def __init__(self, rpm: int):
        if rpm <= 0:
            raise ValueError(f"rpm must be positive, got {rpm}")
        self.rpm = rpm
        self._interval = 60.0 / rpm
        self._last_call: float = 0.0
        self._lock = asyncio.Lock()
        self._total_requests: int = 0
        self._total_waited_ms: float = 0.0

    async def acquire(self) -> float:
        """Wait if needed, then record the call. Returns ms waited."""
        async with self._lock:
            now = time.monotonic()
            wait = self._interval - (now - self._last_call)
            waited = 0.0
            if wait > 0:
                await asyncio.sleep(wait)
                waited = wait * 1000
            self._last_call = time.monotonic()
            self._total_requests += 1
            self._total_waited_ms += waited
            if waited > 50:
                logger.debug("Rate limiter delayed request", wait_ms=round(waited), rpm=self.rpm)
            return waited

    @property
    def stats(self) -> dict:
        return {
            "rpm": self.rpm,
            "total_requests": self._total_requests,
            "avg_wait_ms": round(self._total_waited_ms / max(self._total_requests, 1), 1),
        }


class AdaptiveRateLimiter(RateLimiter):
    """
    Self-tuning rate limiter.

    Every PROBE_INTERVAL_DAYS it tries running at base_rpm * (1 + PROBE_FACTOR).
    If the probe window passes with fewer than MAX_PROBE_ERRORS 429 responses,
    the higher rate becomes the new standard.
    If errors are detected the probe is aborted and the base rate is restored.

    State is persisted to .rate_state.json so probing survives restarts.
    Probes are never resumed mid-window after a restart (safer).
    """

    def __init__(self, rpm: int, client_name: str = "default"):
        super().__init__(rpm)
        self._client_name = client_name
        self._base_rpm: int = rpm
        self._in_probe: bool = False
        self._probe_start: float = 0.0
        self._probe_errors: int = 0
        self._last_probe_check: float = 0.0   # epoch seconds
        self._load_state()

    # ── persistence ──────────────────────────────────────────────────────────

    def _load_state(self) -> None:
        try:
            data = json.loads(_STATE_FILE.read_text())
            c = data.get(self._client_name, {})
            self._base_rpm = c.get("base_rpm", self._base_rpm)
            self._last_probe_check = c.get("last_probe_check", 0.0)
            self.rpm = self._base_rpm
            self._interval = 60.0 / self.rpm
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            pass

    def _save_state(self) -> None:
        try:
            data: dict = {}
            if _STATE_FILE.exists():
                try:
                    data = json.loads(_STATE_FILE.read_text())
                except json.JSONDecodeError:
                    data = {}
            data[self._client_name] = {
                "base_rpm": self._base_rpm,
                "last_probe_check": self._last_probe_check,
            }
            _STATE_FILE.write_text(json.dumps(data, indent=2))
        except OSError as e:
            logger.warning("Rate state save failed", error=str(e))

    # ── probe lifecycle ───────────────────────────────────────────────────────

    def _maybe_start_probe(self) -> None:
        if self._in_probe:
            return
        if time.time() - self._last_probe_check >= _PROBE_INTERVAL_DAYS * 86400:
            new_rpm = max(1, int(self._base_rpm * (1 + _PROBE_FACTOR)))
            self.rpm = new_rpm
            self._interval = 60.0 / new_rpm
            self._in_probe = True
            self._probe_start = time.time()
            self._probe_errors = 0
            logger.info(
                "Rate limit probe started",
                client=self._client_name,
                base_rpm=self._base_rpm,
                probe_rpm=new_rpm,
            )

    def _check_probe_outcome(self) -> None:
        if not self._in_probe:
            return
        elapsed_hours = (time.time() - self._probe_start) / 3600
        if elapsed_hours >= _PROBE_DURATION_HOURS and self._probe_errors == 0:
            self._commit_probe()

    def _commit_probe(self) -> None:
        old = self._base_rpm
        self._base_rpm = self.rpm
        self._in_probe = False
        self._last_probe_check = time.time()
        self._save_state()
        logger.info(
            "Rate limit probe succeeded — new standard",
            client=self._client_name,
            old_rpm=old,
            new_rpm=self._base_rpm,
        )

    def _revert_probe(self) -> None:
        self.rpm = self._base_rpm
        self._interval = 60.0 / self._base_rpm
        self._in_probe = False
        self._last_probe_check = time.time()
        self._save_state()
        logger.warning(
            "Rate limit probe failed — reverted",
            client=self._client_name,
            rpm=self._base_rpm,
        )

    def record_rate_limit_error(self) -> None:
        """Call when the upstream API returns 429. Aborts probe after MAX_PROBE_ERRORS."""
        if not self._in_probe:
            return
        self._probe_errors += 1
        logger.debug(
            "Rate limit 429 during probe",
            client=self._client_name,
            errors=self._probe_errors,
            threshold=_MAX_PROBE_ERRORS,
        )
        if self._probe_errors >= _MAX_PROBE_ERRORS:
            self._revert_probe()

    # ── override acquire ──────────────────────────────────────────────────────

    async def acquire(self) -> float:
        self._maybe_start_probe()
        self._check_probe_outcome()
        return await super().acquire()
