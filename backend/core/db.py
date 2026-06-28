import logging
from urllib.parse import urlparse, urlencode, parse_qs, urlunparse

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.exc import ProgrammingError

from config.settings import get_settings

settings = get_settings()

Base = declarative_base()
_engine = None


_LIBPQ_ONLY_PARAMS = {"sslmode", "channel_binding", "gssencmode", "connect_timeout", "sslcert", "sslkey", "sslrootcert"}


def _get_url() -> tuple[str, bool]:
    """Returns (asyncpg_url, ssl_required). Strips libpq-only params asyncpg rejects."""
    database_url = settings.database.url
    if not database_url:
        return "", False
    # SQLite URLs have no libpq params to strip; urlunparse corrupts them by
    # dropping the empty netloc component (///  → /). Return as-is.
    if database_url.startswith("sqlite"):
        return database_url, False
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    parsed = urlparse(database_url)
    params = parse_qs(parsed.query)
    sslmode = params.pop("sslmode", [None])[0]
    ssl_required = sslmode in ("require", "verify-full", "verify-ca")
    for p in _LIBPQ_ONLY_PARAMS - {"sslmode"}:
        params.pop(p, None)
    new_query = urlencode({k: v[0] for k, v in params.items()})
    url = urlunparse(parsed._replace(query=new_query))
    return url, ssl_required


def _get_engine():
    global _engine
    if _engine is None:
        url, ssl_required = _get_url()
        if not url:
            raise RuntimeError("DATABASE_URL is not configured")
        kwargs: dict = {"echo": settings.database.echo, "future": True}
        if "sqlite" in url:
            from sqlalchemy.pool import StaticPool
            kwargs["poolclass"] = StaticPool
            kwargs["connect_args"] = {"check_same_thread": False}
        else:
            kwargs["pool_size"] = settings.database.pool_size
            kwargs["max_overflow"] = settings.database.max_overflow
            if ssl_required:
                kwargs["connect_args"] = {"ssl": "require"}
        _engine = create_async_engine(url, **kwargs)
    return _engine


# Provide direct import compatibility
engine = _get_engine()

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def create_tables():
    import models  # noqa: F401
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
