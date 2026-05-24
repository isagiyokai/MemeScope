from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.middleware.rate_limit import RateLimitMiddleware

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

# Warn on insecure config at startup
settings.validate_security()


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


# Disable interactive docs in production
_docs_url = "/docs" if settings.app.env == "development" else None
_redoc_url = "/redoc" if settings.app.env == "development" else None
_openapi_url = "/openapi.json" if settings.app.env == "development" else None

app = FastAPI(
    title=settings.app.name,
    version=settings.app.version,
    description="MemeScope behavioral intelligence engine.",
    lifespan=lifespan,
    docs_url=_docs_url,
    redoc_url=_redoc_url,
    openapi_url=_openapi_url,
)

# Never combine allow_origins=["*"] with allow_credentials=True (browser security).
# When origins are explicit, credentials (cookies/auth headers) are allowed.
_wildcard = settings.app.cors_origins == ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.app.cors_origins,
    allow_credentials=not _wildcard,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RateLimitMiddleware, calls=200, period=60)

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
    return {"status": "ok"}
