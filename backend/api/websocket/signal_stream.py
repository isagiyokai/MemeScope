import asyncio
import json
from datetime import datetime, timezone
from typing import Optional

from fastapi import WebSocket, WebSocketDisconnect

from core.redis import get_redis
from config.logging import get_logger

logger = get_logger(__name__)
SIGNAL_PUBSUB_CHANNEL = "memescope:signals"


async def signal_stream(websocket: WebSocket):
    await websocket.accept()
    logger.info("WebSocket client connected", client=websocket.client)
    redis = None
    pubsub = None
    task = None

    try:
        redis = await get_redis()
        pubsub = redis.pubsub()
        await pubsub.subscribe(SIGNAL_PUBSUB_CHANNEL)

        async def relay():
            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        data = message["data"]
                        if isinstance(data, bytes):
                            data = data.decode("utf-8")
                        payload = json.loads(data)
                        await websocket.send_json(payload)
                    except Exception as e:
                        logger.error("WebSocket relay error", error=str(e))

        task = asyncio.create_task(relay())

        while True:
            try:
                await asyncio.sleep(10)
                await websocket.send_json({"type": "ping", "ts": datetime.now(timezone.utc).isoformat()})
            except WebSocketDisconnect:
                break
            except Exception:
                break

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected", client=websocket.client)
    except Exception as e:
        logger.error("WebSocket error", error=str(e))
    finally:
        if task is not None:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        if pubsub is not None:
            await pubsub.unsubscribe(SIGNAL_PUBSUB_CHANNEL)
            await pubsub.close()
