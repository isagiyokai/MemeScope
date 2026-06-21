from datetime import datetime, timezone
from typing import Optional, Sequence, Any

from sqlalchemy.ext.asyncio import AsyncSession

from clients.pumpapi_client import PumpAPIClient
from repositories.token_repo import TokenRepository
from repositories.wallet_repo import WalletRepository
from schemas.token_schema import TokenCreate
from schemas.wallet_schema import WalletCreate
from config.logging import get_logger
from config.constants import PUMPFUN_PROGRAM

logger = get_logger(__name__)


class PumpfunTracker:
    """
    Tracks Pump.fun launches via PumpAPI, persists token metadata,
    and captures first buyers / creator wallets for downstream intelligence.
    """

    def __init__(self, session: AsyncSession, client: Optional[PumpAPIClient] = None):
        self.session = session
        self.client = client or PumpAPIClient()
        self.token_repo = TokenRepository(session)
        self.wallet_repo = WalletRepository(session)

    async def ingest_latest_launches(self, limit: int = 50) -> list[Any]:
        """Fetch latest Pump.fun launches and persist new tokens."""
        launches = await self.client.get_latest_launches(limit=limit)
        created = []
        for launch in launches:
            mint = launch.get("mint") or launch.get("token_mint") or launch.get("mint_address")
            if not mint:
                continue
            existing = await self.token_repo.get_by_mint(mint)
            if existing:
                continue
            token_data = TokenCreate(
                mint_address=mint,
                name=launch.get("name"),
                symbol=launch.get("symbol"),
                decimals=launch.get("decimals", 6),
                total_supply=launch.get("total_supply"),
                circulating_supply=launch.get("circulating_supply"),
                creator_wallet=launch.get("creator"),
                launch_platform="pumpfun",
                launch_timestamp=datetime.now(timezone.utc),
                current_price=launch.get("price"),
                market_cap=launch.get("market_cap"),
                liquidity_usd=launch.get("liquidity"),
                volume_24h=launch.get("volume_24h"),
                holder_count=launch.get("holder_count"),
                is_tracking=True,
            )
            try:
                token = await self.token_repo.create(token_data)
                created.append(token)
                logger.info("Pump.fun launch ingested", mint=mint, name=token_data.name)
            except Exception as e:
                logger.error("Failed to ingest Pump.fun launch", mint=mint, error=str(e))
        return created

    async def ingest_launch_detail(self, mint: str) -> Optional[Any]:
        """Fetch and enrich a specific Pump.fun launch with first buyers + creator."""
        launch = await self.client.get_launch(mint)
        if not launch:
            return None

        token = await self.token_repo.get_by_mint(mint)
        if not token:
            token_data = TokenCreate(
                mint_address=mint,
                name=launch.get("name"),
                symbol=launch.get("symbol"),
                decimals=launch.get("decimals", 6),
                total_supply=launch.get("total_supply"),
                circulating_supply=launch.get("circulating_supply"),
                creator_wallet=launch.get("creator"),
                launch_platform="pumpfun",
                launch_timestamp=datetime.now(timezone.utc),
                current_price=launch.get("price"),
                market_cap=launch.get("market_cap"),
                liquidity_usd=launch.get("liquidity"),
                volume_24h=launch.get("volume_24h"),
                holder_count=launch.get("holder_count"),
                is_tracking=True,
            )
            token = await self.token_repo.create(token_data)

        # Persist creator wallet if not exists
        creator = launch.get("creator") or launch.get("creator_wallet")
        if creator:
            existing_wallet = await self.wallet_repo.get_by_address(creator)
            if not existing_wallet:
                await self.wallet_repo.create(WalletCreate(address=creator))
            await self.token_repo.update_price(mint, token.current_price or 0.0)
            # Note: token_repo doesn't have a direct update for creator, but we can update via session if needed
            # For now, creator is stored at creation time

        # Persist first buyers as wallet stubs
        first_buyers = await self.client.get_first_buyers(mint)
        for buyer in first_buyers:
            addr = buyer.get("wallet") or buyer.get("buyer") or buyer.get("address")
            if not addr:
                continue
            existing = await self.wallet_repo.get_by_address(addr)
            if not existing:
                try:
                    await self.wallet_repo.create(WalletCreate(address=addr))
                except Exception as e:
                    logger.error("Failed to persist first buyer wallet", wallet=addr, error=str(e))

        logger.info("Pump.fun launch detail ingested", mint=mint, buyers=len(first_buyers), creator=creator)
        return token

    async def process_raw_launch(self, raw_launch: dict) -> Optional[Any]:
        """Process a single PumpAPI launch dict from the queue."""
        mint = raw_launch.get("mint") or raw_launch.get("token_mint") or raw_launch.get("mint_address")
        if not mint:
            logger.warning("Pumpfun raw launch missing mint", raw=raw_launch)
            return None

        existing = await self.token_repo.get_by_mint(mint)
        if existing:
            # Already tracked; optionally update metadata
            return existing

        token_data = TokenCreate(
            mint_address=mint,
            name=raw_launch.get("name"),
            symbol=raw_launch.get("symbol"),
            decimals=raw_launch.get("decimals", 6),
            total_supply=raw_launch.get("total_supply"),
            circulating_supply=raw_launch.get("circulating_supply"),
            creator_wallet=raw_launch.get("txSigner") or raw_launch.get("creator") or raw_launch.get("creator_wallet"),
            launch_platform="pumpfun",
            launch_timestamp=datetime.now(timezone.utc),
            current_price=raw_launch.get("price"),
            market_cap=raw_launch.get("market_cap"),
            liquidity_usd=raw_launch.get("liquidity"),
            volume_24h=raw_launch.get("volume_24h"),
            holder_count=raw_launch.get("holder_count"),
            is_tracking=True,
        )
        try:
            token = await self.token_repo.create(token_data)
            logger.info("Pump.fun launch persisted from queue", mint=mint, name=token_data.name)
        except Exception as e:
            logger.error("Failed to persist Pump.fun launch from queue", mint=mint, error=str(e))
            return None

        # Persist creator wallet — PumpAPI uses txSigner for creator address
        creator = raw_launch.get("txSigner") or raw_launch.get("creator") or raw_launch.get("creator_wallet")
        if creator:
            existing_wallet = await self.wallet_repo.get_by_address(creator)
            if not existing_wallet:
                await self.wallet_repo.create(WalletCreate(address=creator))

        # Persist first buyers from raw launch if present
        first_buyers = raw_launch.get("first_buyers") or raw_launch.get("buyers") or []
        for buyer in first_buyers:
            addr = buyer.get("wallet") or buyer.get("buyer") or buyer.get("address")
            if not addr:
                continue
            existing = await self.wallet_repo.get_by_address(addr)
            if not existing:
                try:
                    await self.wallet_repo.create(WalletCreate(address=addr))
                except Exception as e:
                    logger.error("Failed to persist first buyer from queue", wallet=addr, error=str(e))

        logger.info("Pump.fun raw launch processed", mint=mint, creator=creator, buyers=len(first_buyers))
        return token

    async def run(self, limit: int = 50) -> list[Any]:
        """Default run: ingest latest launches."""
        return await self.ingest_latest_launches(limit=limit)

    async def close(self):
        await self.client.close()
