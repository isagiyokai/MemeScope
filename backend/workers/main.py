"""Single worker process — runs all 4 workers concurrently via asyncio.gather."""
import asyncio
from config.logging import get_logger

logger = get_logger(__name__)


async def main():
    from workers.parser_worker import run_parser_worker
    from workers.signal_worker import run_signal_worker
    from workers.holder_worker import run_holder_worker
    from workers.pumpfun_worker import run_pumpfun_worker

    logger.info("Starting all workers")
    await asyncio.gather(
        run_parser_worker(),
        run_signal_worker(),
        run_holder_worker(),
        run_pumpfun_worker(),
    )


if __name__ == "__main__":
    asyncio.run(main())
