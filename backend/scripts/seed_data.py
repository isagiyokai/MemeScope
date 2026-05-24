import asyncio
from datetime import datetime, timezone

from core.db import AsyncSessionLocal
from repositories.token_repo import TokenRepository
from repositories.wallet_repo import WalletRepository
from schemas.token_schema import TokenCreate
from schemas.wallet_schema import WalletCreate
from config.logging import configure_logging, get_logger

configure_logging()
logger = get_logger(__name__)


async def seed_tokens() -> None:
    async with AsyncSessionLocal() as session:
        repo = TokenRepository(session)
        seeds = [
            TokenCreate(
                mint_address='So11111111111111111111111111111111111111112',
                name='Wrapped SOL',
                symbol='WSOL',
                decimals=9,
                launch_platform='native',
                is_tracking=True,
            ),
            TokenCreate(
                mint_address='EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v',
                name='USD Coin',
                symbol='USDC',
                decimals=6,
                launch_platform='native',
                is_tracking=True,
            ),
        ]
        created = 0
        for data in seeds:
            existing = await repo.get_by_mint(data.mint_address)
            if not existing:
                await repo.create(data)
                created += 1
                logger.info('Seeded token', mint=data.mint_address, name=data.name)
        logger.info('Token seeding complete', created=created)


async def seed_wallets() -> None:
    async with AsyncSessionLocal() as session:
        repo = WalletRepository(session)
        known = [
            '5Q544fKrFoe6tsEbD7S8EmxGTJYAKtTVhAW5Q5pge4j1',
        ]
        created = 0
        for addr in known:
            existing = await repo.get_by_address(addr)
            if not existing:
                await repo.create(WalletCreate(address=addr, tags='seeded'))
                created += 1
                logger.info('Seeded wallet', wallet=addr)
        logger.info('Wallet seeding complete', created=created)


async def main():
    await seed_tokens()
    await seed_wallets()
    logger.info('All seeding complete.')


if __name__ == '__main__':
    asyncio.run(main())