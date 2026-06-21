import asyncio
import os
from logging.config import fileConfig
from urllib.parse import urlparse, urlencode, parse_qs, urlunparse

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine

from alembic import context
from core.db import Base
from config.settings import get_settings

settings = get_settings()


_LIBPQ_ONLY_PARAMS = {"sslmode", "channel_binding", "gssencmode", "connect_timeout", "sslcert", "sslkey", "sslrootcert"}


def _make_asyncpg_url(raw: str) -> tuple[str, bool]:
    """Convert a postgres:// URL to asyncpg dialect, strip libpq-only params.
    Returns (url, ssl_required)."""
    if raw.startswith("postgres://"):
        raw = raw.replace("postgres://", "postgresql+asyncpg://", 1)
    elif raw.startswith("postgresql://"):
        raw = raw.replace("postgresql://", "postgresql+asyncpg://", 1)
    parsed = urlparse(raw)
    params = parse_qs(parsed.query)
    sslmode = params.pop("sslmode", [None])[0]
    ssl_required = sslmode in ("require", "verify-full", "verify-ca")
    for p in _LIBPQ_ONLY_PARAMS - {"sslmode"}:
        params.pop(p, None)
    new_query = urlencode({k: v[0] for k, v in params.items()})
    url = urlunparse(parsed._replace(query=new_query))
    return url, ssl_required


url, _ssl_required = _make_asyncpg_url(settings.database.url)

config = context.config
config.set_main_option("sqlalchemy.url", url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connect_args = {"ssl": "require"} if _ssl_required else {}
    connectable = create_async_engine(url, poolclass=pool.NullPool, connect_args=connect_args)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
