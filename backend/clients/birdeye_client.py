import asyncio
from typing import Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from config.settings import get_settings
from config.logging import get_logger
from utils.rate_limiter import AdaptiveRateLimiter

logger = get_logger(__name__)
settings = get_settings()

RETRYABLE = (httpx.HTTPStatusError, httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError)
BIRDEYE_RPM = 60


class BirdeyeClient:
    def __init__(self):
        self.base_url = settings.birdeye.base_url.rstrip("/")
        self.api_key = settings.birdeye.api_key
        self.timeout = settings.birdeye.request_timeout
        self.headers = {
            "X-API-KEY": self.api_key,
            "Accept": "application/json",
            "x-chain": "solana",
        }
        self.client: Optional[httpx.AsyncClient] = None
        self._limiter = AdaptiveRateLimiter(rpm=BIRDEYE_RPM, client_name="birdeye")

    async def _get_client(self) -> httpx.AsyncClient:
        if self.client is None or self.client.is_closed:
            self.client = httpx.AsyncClient(headers=self.headers, timeout=self.timeout)
        return self.client

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(RETRYABLE),
        reraise=True,
    )
    async def _get(self, path: str, params: Optional[dict] = None) -> dict:
        await self._limiter.acquire()
        client = await self._get_client()
        url = f"{self.base_url}{path}"
        response = await client.get(url, params=params)
        if response.status_code == 429:
            self._limiter.record_rate_limit_error()
        response.raise_for_status()
        data = response.json()
        if not data.get("success"):
            logger.warning("Birdeye API non-success", path=path, response=data)
        return data.get("data", {})

    async def get_token_price(self, token_mint: str) -> Optional[float]:
        try:
            data = await self._get("/defi/price", {"address": token_mint})
            return data.get("value")
        except Exception as e:
            logger.error("get_token_price failed", token=token_mint, error=str(e))
            return None

    async def get_token_ohlc(self, token_mint: str, timeframe: str = "1m", limit: int = 100) -> list[dict]:
        try:
            data = await self._get(
                "/defi/ohlcv",
                {"address": token_mint, "timeframe": timeframe, "limit": limit},
            )
            return data if isinstance(data, list) else []
        except Exception as e:
            logger.error("get_token_ohlc failed", token=token_mint, error=str(e))
            return []

    async def get_token_trades(self, token_mint: str, limit: int = 100) -> list[dict]:
        try:
            data = await self._get(
                "/defi/txs/token",
                {"address": token_mint, "limit": limit},
            )
            return data if isinstance(data, list) else []
        except Exception as e:
            logger.error("get_token_trades failed", token=token_mint, error=str(e))
            return []

    async def get_wallet_transactions(self, wallet: str, limit: int = 50) -> list[dict]:
        try:
            data = await self._get(
                "/v1/wallet/tx_list",
                {"wallet": wallet, "limit": limit},
            )
            return data if isinstance(data, list) else []
        except Exception as e:
            logger.error("get_wallet_transactions failed", wallet=wallet, error=str(e))
            return []

    async def close(self):
        if self.client and not self.client.is_closed:
            await self.client.aclose()
