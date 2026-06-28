"""Single worker process — runs all 4 workers concurrently via asyncio.gather.

Also binds a minimal HTTP server so Render's web service health check passes.
"""
import asyncio
import os
from config.logging import get_logger

logger = get_logger(__name__)


async def _health_server():
    """Minimal HTTP server so Render web service health check passes."""
    from aiohttp import web

    async def health(request):
        return web.Response(text='{"status":"ok"}', content_type="application/json")

    app = web.Application()
    app.router.add_get("/health", health)
    app.router.add_get("/", health)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8001))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info("Worker health server listening", port=port)


async def main():
    from workers.parser_worker import run_parser_worker
    from workers.signal_worker import run_signal_worker
    from workers.holder_worker import run_holder_worker
    from workers.pumpfun_worker import run_pumpfun_worker
    from services.ingestion.ingestion import PumpfunListener
    from config.settings import get_settings

    logger.info("Starting all workers")
    listener = PumpfunListener()
    logger.info("PumpfunListener instantiated — scheduling in gather")

    tasks = [
        _health_server(),
        run_parser_worker(),
        run_signal_worker(),
        run_holder_worker(),
        run_pumpfun_worker(),
        listener.run(),
    ]

    settings = get_settings()
    if settings.archive.enabled:
        try:
            from services.archive.duckdb_backend import DuckDBArchiveBackend
            from services.archive.archive_writer import ArchiveWriter
            backend = DuckDBArchiveBackend(settings.archive.path)
            writer = ArchiveWriter(backend)
            tasks.append(writer.run())
            logger.info("ArchiveWriter enabled", path=settings.archive.path)
        except Exception as e:
            logger.error("ArchiveWriter failed to start — continuing without archive", error=str(e))

    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
