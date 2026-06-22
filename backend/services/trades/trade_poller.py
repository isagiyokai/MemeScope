import asyncio
import json
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from clients.helius_client import HeliusClient
from core.redis import get_redis
from repositories.token_repo import TokenRepository
from config.logging import get_logger

logger = get_logger(__name__)

RAW_TX_QUEUE = "raw_tx_queue"


class TradePoller:
    """
    Polls Helius getSignaturesForAddress for each tracked token and pushes
    raw transactions to raw_tx_queue for the parser_worker to decode.

    Uses last_trade_sig on the token as a cursor to avoid re-fetching known txs.
    Helius returns signatures newest → oldest, so we collect until we hit the cursor.
    """

    def __init__(self, session: AsyncSession, client: Optional[HeliusClient] = None):
        self.session = session
        self.client = client or HeliusClient()
        self.token_repo = TokenRepository(session)

    async def poll_token(self, token) -> int:
        """Fetch new signatures for a token and enqueue raw txs. Returns count enqueued."""
        cursor = token.last_trade_sig
        try:
            sigs = await self.client.get_signatures_for_address(token.mint_address, limit=50)
        except Exception as e:
            logger.error("Helius get_signatures failed", mint=token.mint_address, error=str(e))
            return 0

        if not sigs:
            return 0

        # Collect new sigs until we reach the stored cursor (newest → oldest order)
        new_entries = []
        for entry in sigs:
            sig = entry.get("signature")
            if not sig:
                continue
            if sig == cursor:
                break
            new_entries.append((sig, entry))

        if not new_entries:
            return 0

        redis = await get_redis()
        enqueued = 0

        # Push oldest first so parser_worker processes in chronological order
        for sig, entry in reversed(new_entries):
            try:
                tx = await self.client.get_parsed_transaction(sig)
                payload = {
                    "signature": sig,
                    "transaction": tx,
                    "slot": entry.get("slot"),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                await redis.lpush(RAW_TX_QUEUE, json.dumps(payload))
                enqueued += 1
                await asyncio.sleep(0.1)
            except Exception as e:
                logger.error("Failed to fetch/enqueue tx", sig=sig[:12], mint=token.mint_address, error=str(e))

        # Advance cursor to newest sig seen
        newest_sig = new_entries[0][0]
        try:
            await self.token_repo.update_last_trade_sig(token.mint_address, newest_sig)
        except Exception as e:
            logger.error("Failed to update last_trade_sig cursor", mint=token.mint_address, error=str(e))

        logger.info("Trade poll done", mint=token.mint_address, enqueued=enqueued, new_sigs=len(new_entries))
        return enqueued

    async def poll_all_tracked(self, limit: int = 30) -> dict[str, int]:
        """Poll the `limit` most recently updated tracked tokens."""
        tokens = await self.token_repo.list_tracking(limit=limit)
        results: dict[str, int] = {}
        for token in tokens:
            try:
                count = await self.poll_token(token)
                results[token.mint_address] = count
                await asyncio.sleep(0.3)
            except Exception as e:
                logger.error("TradePoller error for token", mint=token.mint_address, error=str(e))
                results[token.mint_address] = 0
        return results

    async def close(self):
        await self.client.close()
