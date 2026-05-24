import asyncio
import sys

from core.db import create_tables, engine
from core.redis import redis_health_check
from config.logging import configure_logging, get_logger

configure_logging()
logger = get_logger(__name__)


async def main():
    logger.info("Initializing database...")
    try:
        await create_tables()
        logger.info("Database tables created successfully.")
    except Exception as e:
        logger.error("Database initialization failed", error=str(e))
        sys.exit(1)

    try:
        redis_ok = await redis_health_check()
        if redis_ok:
            logger.info("Redis connection OK.")
        else:
            logger.warning("Redis connection failed.")
    except Exception as e:
        logger.warning("Redis check error", error=str(e))

    logger.info("Init complete.")


if __name__ == "__main__":
    asyncio.run(main())
