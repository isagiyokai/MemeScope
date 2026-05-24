"""
PumpAPI WebSocket client — wss://stream.pumpapi.io/

Events stream continuously (no subscription needed, no auth).
Filter by txType: "create" (launches), "trade" (buys/sells), "transfer", "migration", etc.

Create event key fields: mint, name, symbol, txSigner (creator), timestamp, signature
Trade event key fields: mint, txSigner, solAmount, tokenAmount, isBuy, timestamp, signature
"""
import asyncio
import json
from typing import Callable, Awaitable, Optional

import websockets
from websockets.exceptions import ConnectionClosed, WebSocketException

from config.logging import get_logger

logger = get_logger(__name__)

STREAM_URL = "wss://stream.pumpapi.io/"


class PumpAPIClient:
    def __init__(self, stream_url: str = STREAM_URL):
        self.stream_url = stream_url
        self._ws: Optional[websockets.WebSocketClientProtocol] = None
        self._closed = False

    async def stream_events(
        self,
        callback: Callable[[dict], Awaitable[None]],
        reconnect_delay: float = 5.0,
    ) -> None:
        """
        Connect and stream all events, calling callback for each.
        Reconnects automatically on disconnect until close() is called.
        """
        while not self._closed:
            try:
                async with websockets.connect(
                    self.stream_url,
                    ping_interval=30,
                    ping_timeout=10,
                ) as ws:
                    self._ws = ws
                    logger.info("PumpAPI stream connected", url=self.stream_url)
                    async for raw in ws:
                        if self._closed:
                            break
                        try:
                            event = json.loads(raw if isinstance(raw, str) else raw.decode("utf-8"))
                            await callback(event)
                        except json.JSONDecodeError:
                            logger.warning("PumpAPI bad JSON", raw=str(raw)[:200])
                        except Exception as e:
                            logger.error("PumpAPI callback error", error=str(e))
            except ConnectionClosed as e:
                if self._closed:
                    break
                logger.warning("PumpAPI stream disconnected, reconnecting", reason=str(e), delay=reconnect_delay)
                await asyncio.sleep(reconnect_delay)
            except WebSocketException as e:
                if self._closed:
                    break
                logger.error("PumpAPI WebSocket error, reconnecting", error=str(e), delay=reconnect_delay)
                await asyncio.sleep(reconnect_delay)
            except Exception as e:
                if self._closed:
                    break
                logger.error("PumpAPI unexpected error, reconnecting", error=str(e), delay=reconnect_delay)
                await asyncio.sleep(reconnect_delay)

    async def connect_once(self, timeout: float = 30.0) -> bool:
        """Try one connection and return True if reachable (for health checks)."""
        async def _try():
            async with websockets.connect(self.stream_url, open_timeout=timeout, ping_interval=None) as ws:
                await ws.recv()
                return True

        try:
            return await asyncio.wait_for(_try(), timeout=timeout)
        except Exception as e:
            logger.error("PumpAPI connect_once failed", error=str(e))
            return False

    async def close(self):
        self._closed = True
        if self._ws and not self._ws.closed:
            await self._ws.close()
