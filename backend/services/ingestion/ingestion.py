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

    _logged_sample = False
    _logged_event_fingerprints: set = set()

    async def _handle_event(self, event: dict) -> None:
        from services import metrics
        metrics.increment("pumpapi_events_total")

        if not PumpfunListener._logged_sample:
            PumpfunListener._logged_sample = True
            logger.info("PumpAPI first event sample", event=event)

        # Normalize txType: raw string may be "buy"/"sell"/"create" or absent
        raw_type = (event.get("txType") or event.get("type") or "").lower()

        if raw_type in ("buy", "sell", "trade"):
            tx_type = "trade"
        elif raw_type == "create":
            tx_type = "create"
        else:
            # Field-presence fallback
            has_trade_fields = (
                "isBuy" in event
                or "solAmount" in event
                or "tokenAmount" in event
                or event.get("traderPublicKey")
                or event.get("trader")
            )
            has_create_fields = (
                event.get("name") and event.get("symbol") and event.get("mint")
            )
            if has_trade_fields:
                tx_type = "trade"
            elif has_create_fields:
                tx_type = "create"
            else:
                tx_type = ""

        logger.debug("PumpAPI event received", tx_type=tx_type, mint=event.get("mint"), sig=str(event.get("signature", ""))[:12])
        try:
            redis = await get_redis()
        except Exception:
            logger.exception("PumpAPI _handle_event: failed to get Redis connection")
            return

        if tx_type == "create":
            metrics.increment("pumpapi_create_events_total")
            try:
                await redis.lpush(PUMPFUN_LAUNCH_QUEUE, json.dumps(event))
                logger.info("Pump.fun launch enqueued", mint=event.get("mint"), name=event.get("name"), symbol=event.get("symbol"))
            except Exception:
                logger.exception("Pump.fun launch enqueue failed", mint=event.get("mint"))

        elif tx_type == "trade":
            metrics.increment("pumpapi_trade_events_total")
            payload = {
                "signature": event.get("signature"),
                "slot": event.get("block") or event.get("slot"),
                "transaction": {
                    "blockTime": event.get("timestamp"),
                    "_pumpapi": event,
                },
            }
            try:
                await redis.lpush(RAW_TX_QUEUE, json.dumps(payload))
                logger.info(
                    "Pump.fun trade enqueued",
                    mint=event.get("mint"),
                    is_buy=event.get("isBuy"),
                    sol=event.get("solAmount"),
                    sig=str(event.get("signature", ""))[:12],
                )
            except Exception:
                logger.exception("Pump.fun trade enqueue failed", mint=event.get("mint"))

        else:
            metrics.increment("pumpapi_dropped_events_total")
            # Log one sample per unique field fingerprint so we can audit unknown formats
            fingerprint = frozenset(event.keys())
            if fingerprint not in PumpfunListener._logged_event_fingerprints:
                PumpfunListener._logged_event_fingerprints.add(fingerprint)
                logger.info(
                    "PumpAPI unhandled event — new field signature",
                    fields=sorted(event.keys()),
                    event=event,
                )
            else:
                logger.debug("PumpAPI unhandled txType", tx_type=raw_type, mint=event.get("mint"))

    async def run(self) -> None:
        """Blocking stream loop — reconnects on disconnect."""
        logger.info("PumpfunListener.run() started — entering stream loop")
        try:
            await self.client.stream_events(self._handle_event)
        except Exception:
            logger.exception("PumpfunListener.run() exited with unhandled exception")

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
