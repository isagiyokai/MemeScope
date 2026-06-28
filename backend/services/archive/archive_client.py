"""Thin async Redis publisher for archive events.

Fire-and-forget — never blocks, never raises. Workers import archive_publish and call it.
"""
from __future__ import annotations

import json
from datetime import datetime, date, timezone
from decimal import Decimal
from uuid import UUID

from core.redis import get_redis
from config.logging import get_logger
from config.settings import get_settings

logger = get_logger(__name__)


class _SafeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, UUID):
            return str(obj)
        return super().default(obj)


async def archive_publish(event_type: str, payload: dict, source: str = "workers") -> None:
    """Publish one event to the archive queue. Silently drops on any error."""
    settings = get_settings()
    if not settings.archive.enabled:
        return
    try:
        redis = await get_redis()
        event = {
            "event_type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": payload,
            "source": source,
        }
        await redis.lpush(settings.archive.queue_name, json.dumps(event, cls=_SafeEncoder))
    except Exception as e:
        logger.warning("Archive publish failed", event_type=event_type, error=str(e))
