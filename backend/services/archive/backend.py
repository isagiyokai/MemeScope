"""Archive backend abstraction.

Swap DuckDB for S3/Parquet/ClickHouse/Postgres without touching workers.
All implementations must be thread-safe — write_batch is called from asyncio.to_thread.
"""
from __future__ import annotations

import abc
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class ArchiveEvent:
    event_type: str
    payload: dict[str, Any]
    source: str = "workers"
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ArchiveBackend(abc.ABC):
    """Write-only archive interface. Implementations must be thread-safe."""

    @abc.abstractmethod
    def write_batch(self, events: list[ArchiveEvent]) -> None:
        """Write a batch of events synchronously. Called from thread pool executor."""
        ...

    @abc.abstractmethod
    def get_db_size_mb(self) -> float:
        """Return current archive size in MB for monitoring."""
        ...

    @abc.abstractmethod
    def close(self) -> None:
        """Release resources."""
        ...
