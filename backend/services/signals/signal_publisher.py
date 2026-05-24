import json
from datetime import datetime
from typing import Any

from core.redis import get_redis
from config.logging import get_logger

logger = get_logger(__name__)
SIGNAL_PUBSUB_CHANNEL = "memescope:signals"


def _serialize_signal(signal: Any) -> dict:
    """Serialize a Signal model instance into a plain dict for pub/sub."""
    st = signal.signal_type
    if hasattr(st, "value"):
        st = st.value
    triggered = signal.triggered_at
    if isinstance(triggered, datetime):
        triggered = triggered.isoformat()
    return {
        "id": str(signal.id),
        "token_mint": signal.token_mint,
        "signal_type": st,
        "confidence": float(signal.confidence),
        "reason": signal.reason,
        "source_rule": signal.source_rule,
        "triggered_at": triggered,
    }


async def publish_signal(signal: Any) -> None:
    try:
        redis = await get_redis()
        payload = json.dumps(_serialize_signal(signal))
        await redis.publish(SIGNAL_PUBSUB_CHANNEL, payload)
        logger.info("Signal published to pub/sub", signal_id=str(signal.id), channel=SIGNAL_PUBSUB_CHANNEL)
    except Exception as e:
        logger.error("Failed to publish signal", error=str(e))


async def publish_json(payload: dict) -> None:
    """Utility to publish arbitrary JSON to the signal channel."""
    try:
        redis = await get_redis()
        await redis.publish(SIGNAL_PUBSUB_CHANNEL, json.dumps(payload))
    except Exception as e:
        logger.error("Failed to publish JSON", error=str(e))
