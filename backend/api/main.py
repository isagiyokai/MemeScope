from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config.settings import get_settings
from config.logging import configure_logging, get_logger
from core.db import create_tables, engine
from core.redis import close_redis
from api.routes import tokens, wallets, holders, signals, clusters, health, stats

try:
    from services.scheduler.jobs import start_scheduler, shutdown_scheduler
    _SCHEDULER_AVAILABLE = True
except ImportError:
    start_scheduler = None
    shutdown_scheduler = None
    _SCHEDULER_AVAILABLE = False

settings = get_settings()
configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up", version=settings.app.version)
    await create_tables()
    if _SCHEDULER_AVAILABLE:
        start_scheduler()
    yield
    if _SCHEDULER_AVAILABLE:
        shutdown_scheduler()
    await engine.dispose()
    await close_redis()
    logger.info("Shutting down")


app = FastAPI(
    title=settings.app.name,
    version=settings.app.version,
    description="MemeScope behavioral intelligence engine.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.app.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api/v1/health", tags=["health"])
app.include_router(stats.router, prefix="/api/v1/stats", tags=["stats"])
app.include_router(tokens.router, prefix="/api/v1/tokens", tags=["tokens"])
app.include_router(wallets.router, prefix="/api/v1/wallets", tags=["wallets"])
app.include_router(holders.router, prefix="/api/v1/holders", tags=["holders"])
app.include_router(signals.router, prefix="/api/v1/signals", tags=["signals"])
app.include_router(clusters.router, prefix="/api/v1/clusters", tags=["clusters"])

from api.websocket.signal_stream import signal_stream
app.add_websocket_route("/ws/signals", signal_stream)


@app.get("/health")
async def health_check():
    return {"status": "ok", "version": settings.app.version}
