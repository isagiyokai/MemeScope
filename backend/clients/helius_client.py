import asyncio
from typing import Optional, Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from config.settings import get_settings
from config.logging import get_logger
from utils.rate_limiter import AdaptiveRateLimiter

logger = get_logger(__name__)
settings = get_settings()

RETRYABLE = (httpx.HTTPStatusError, httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError)


class HeliusClient:
    def __init__(self):
        self.base_url = settings.helius.get_rpc_url()
        self.timeout = settings.helius.request_timeout
        self.max_retries = settings.helius.max_retries
        self.client: Optional[httpx.AsyncClient] = None
        self._limiter = AdaptiveRateLimiter(rpm=settings.helius.rpm, client_name="helius")

    async def _get_client(self) -> httpx.AsyncClient:
        if self.client is None or self.client.is_closed:
            self.client = httpx.AsyncClient(timeout=self.timeout)
        return self.client

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(RETRYABLE),
        reraise=True,
    )
    async def _rpc_call(self, method: str, params: list[Any]) -> dict:
        await self._limiter.acquire()
        client = await self._get_client()
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params,
        }
        response = await client.post(self.base_url, json=payload)
        if response.status_code == 429:
            self._limiter.record_rate_limit_error()
        response.raise_for_status()
        data = response.json()
        if "error" in data:
            raise httpx.HTTPStatusError(
                f"RPC error: {data['error']}", request=response.request, response=response
            )
        return data.get("result", {})

    async def get_token_largest_accounts(self, token_mint: str) -> list[dict]:
        result = await self._rpc_call("getTokenLargestAccounts", [token_mint])
        return result.get("value", [])

    async def get_signatures_for_address(
        self, address: str, limit: int = 100, before: Optional[str] = None
    ) -> list[dict]:
        params = [address, {"limit": limit}]
        if before:
            params[1]["before"] = before
        result = await self._rpc_call("getSignaturesForAddress", params)
        return result if isinstance(result, list) else []

    async def get_parsed_transaction(self, signature: str) -> dict:
        result = await self._rpc_call(
            "getTransaction",
            [signature, {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}],
        )
        return result if isinstance(result, dict) else {}

    async def get_token_accounts_by_owner(self, wallet: str, token_mint: Optional[str] = None) -> list[dict]:
        filters = {"programId": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"}
        if token_mint:
            filters = {"mint": token_mint}
        result = await self._rpc_call(
            "getTokenAccountsByOwner",
            [wallet, filters, {"encoding": "jsonParsed"}],
        )
        return result.get("value", [])

    async def get_account_info(self, address: str) -> dict:
        result = await self._rpc_call("getAccountInfo", [address, {"encoding": "jsonParsed"}])
        return result.get("value", {})

    async def close(self):
        if self.client and not self.client.is_closed:
            await self.client.aclose()
