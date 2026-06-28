"""Archive writer — consumes archive_queue from Redis, batch-writes to ArchiveBackend.

Runs as an asyncio task alongside the production workers.
Never crashes — all exceptions caught and logged.
"""
from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime, timezone

from core.redis import get_redis
from services.archive.backend import ArchiveBackend, ArchiveEvent
from services import metrics
from config.logging import get_logger
from config.settings import get_settings

logger = get_logger(__name__)

_SIZE_LOG_EVERY = 50  # log DB size every N flushes


class ArchiveWriter:
    """
    Reads archive_queue, accumulates up to batch_size events or flush_interval seconds,
    then writes in a thread pool (non-blocking). DuckDB stays off the event loop.
    """

    def __init__(self, backend: ArchiveBackend):
        self._backend = backend
        settings = get_settings()
        self._queue = settings.archive.queue_name
        self._batch_size = settings.archive.batch_size
        self._flush_interval = settings.archive.flush_interval
        self._running = False
        self._flush_count = 0

    async def run(self) -> None:
        self._running = True
        logger.info("ArchiveWriter started", queue=self._queue, batch_size=self._batch_size, flush_interval=self._flush_interval)
        batch: list[ArchiveEvent] = []
        last_flush = time.monotonic()

        while self._running:
            try:
                redis = await get_redis()
                try:
                    result = await redis.brpop(self._queue, timeout=1)
                except Exception as e:
                    logger.warning("ArchiveWriter Redis read error", error=str(e))
                    await asyncio.sleep(2)
                    continue

                if result:
                    _, raw = result
                    try:
                        data = json.loads(raw)
                        batch.append(ArchiveEvent(
                            event_type=data["event_type"],
                            payload=data.get("payload", {}),
                            source=data.get("source", "workers"),
                            timestamp=data.get("timestamp", datetime.now(timezone.utc).isoformat()),
                        ))
                    except Exception as e:
                        logger.warning("ArchiveWriter malformed event", error=str(e))

                now = time.monotonic()
                should_flush = (
                    len(batch) >= self._batch_size
                    or (batch and (now - last_flush) >= self._flush_interval)
                )
                if should_flush:
                    await self._flush(batch)
                    batch = []
                    last_flush = now

            except Exception as e:
                logger.error("ArchiveWriter loop error", error=str(e))
                await asyncio.sleep(2)

    async def _flush(self, batch: list[ArchiveEvent]) -> None:
        if not batch:
            return
        t0 = time.monotonic()
        try:
            await asyncio.to_thread(self._backend.write_batch, batch)
            elapsed_ms = int((time.monotonic() - t0) * 1000)
            metrics.increment("archive_events_written_total", len(batch))
            metrics.increment("archive_batch_duration_ms", elapsed_ms)
            self._flush_count += 1

            if self._flush_count % _SIZE_LOG_EVERY == 0:
                size_mb = await asyncio.to_thread(self._backend.get_db_size_mb)
                metrics.increment("archive_db_size_mb", int(size_mb))
                logger.info("Archive status", db_size_mb=round(size_mb, 2), total_written=metrics.get_all().get("archive_events_written_total", 0))

            logger.debug("Archive batch written", count=len(batch), ms=elapsed_ms)
        except Exception as e:
            metrics.increment("archive_write_failures_total")
            logger.error("Archive flush failed", count=len(batch), error=str(e))

    async def _report_queue_depth(self, redis) -> None:
        try:
            depth = await redis.llen(self._queue)
            metrics.increment("archive_queue_depth", depth - metrics.get_all().get("archive_queue_depth", 0))
        except Exception:
            pass

    def stop(self) -> None:
        self._running = False
