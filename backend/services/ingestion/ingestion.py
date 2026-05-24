import asyncio
import json
from datetime import datetime, timezone
from typing import Optional, Any

from core.redis import get_redis
from clients.helius_client import HeliusClient
from config.settings import get_settings
from config.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

RAW_TX_QUEUE = "raw_tx_queue"
PUMPFUN_LAUNCH_QUEUE = "pumpfun_launch_queue"
SIGNAL_EVAL_QUEUE = "signal_eval_queue"
RETRYABLE = (httpx.HTTPStatusError, httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError)


class HeliusListener:
    """
    Polls Helius RPC for signatures and fetches parsed transactions,
    enqueuing raw transaction blobs to Redis for the parser worker.
    """

    def __init__(self, client: Optional[HeliusClient] = None):
        self.client = client or HeliusClient()
        self.last_seen: dict[str, Optional[str]] = {}

    async def poll_address(self, address: str, limit: int = 50) -> list[dict]:
        """Fetch latest signatures for an address and enqueue raw txs."""
        before = self.last_seen.get(address)
        sigs = await self.client.get_signatures_for_address(address, limit=limit, before=before)
        if not sigs:
            return []
        enqueued = []
        for entry in sigs:
            sig = entry.get("signature")
            if not sig:
                continue
            try:
                tx = await self.client.get_parsed_transaction(sig)
                payload = {
                    "signature": sig,
                    "transaction": tx,
                    "slot": entry.get("slot"),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                redis = await get_redis()
                await redis.lpush(RAW_TX_QUEUE, json.dumps(payload))
                enqueued.append(sig)
            except Exception as e:
                logger.error("Helius tx fetch failed", signature=sig, error=str(e))
        if sigs:
            self.last_seen[address] = sigs[0].get("signature")
        return enqueued

    async def poll_token_mints(self, mints: list[str], limit: int = 50) -> dict[str, int]:
        """Poll token accounts (e.g., mint address as a token program account) for new activity."""
        results = {}
        for mint in mints:
            try:
                # For Solana tokens, mint address itself is an account we can poll signatures for
                sigs = await self.poll_address(mint, limit=limit)
                results[mint] = len(sigs)
                await asyncio.sleep(0.5)
            except Exception as e:
                logger.error("Poll token mint failed", mint=mint, error=str(e))
        return results

    async def close(self):
        await self.client.close()


class PumpfunListener:
    """
    Streams Pump.fun events from PumpAPI WebSocket (wss://stream.pumpapi.io/).
    Routes create events -> pumpfun_launch_queue
    Routes trade events  -> raw_tx_queue (parsed by parser_worker)
    """

    def __init__(self):
        from clients.pumpapi_client import PumpAPIClient
        self.client = PumpAPIClient()

    async def _handle_event(self, event: dict) -> None:
        tx_type = event.get("txType", "")
        redis = await get_redis()

        if tx_type == "create":
            # New token launch — enqueue for pumpfun_worker
            await redis.lpush(PUMPFUN_LAUNCH_QUEUE, json.dumps(event))
            logger.info("Pump.fun launch enqueued", mint=event.get("mint"))

        elif tx_type == "trade":
            # Buy/sell — normalise into raw_tx_queue format for parser_worker
            payload = {
                "signature": event.get("signature"),
                "slot": event.get("block"),
                "transaction": {
                    "blockTime": event.get("timestamp"),
                    "_pumpapi": event,  # parser can read raw event fields
                },
            }
            await redis.lpush(RAW_TX_QUEUE, json.dumps(payload))

    async def run(self) -> None:
        """Blocking stream loop — reconnects on disconnect."""
        await self.client.stream_events(self._handle_event)

    async def close(self):
        await self.client.close()



class PriceFetcher:
    """
    Periodic price fetcher using Birdeye API.
    Updates token prices in DB via repository.
    """

    def __init__(self):
        from clients.birdeye_client import BirdeyeClient
        self.client = BirdeyeClient()

    async def refresh_prices(self, token_repo, mints: list[str]) -> dict[str, Optional[float]]:
        prices = {}
        for mint in mints:
            try:
                price = await self.client.get_token_price(mint)
                if price is not None:
                    await token_repo.update_price(mint, price)
                prices[mint] = price
                await asyncio.sleep(0.2)
            except Exception as e:
                logger.error("Price refresh failed", mint=mint, error=str(e))
                prices[mint] = None
        return prices

    async def close(self):
        await self.client.close()
