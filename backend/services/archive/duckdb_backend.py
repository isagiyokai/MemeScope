"""DuckDB archive backend — persistent analytical cold storage.

NOTE on Render: Render's default filesystem is ephemeral (data lost on restart).
For persistence, mount a Render Disk at /data and set:
  ARCHIVE_PATH=/data/memescope_archive.duckdb
Alternatively, use MotherDuck by setting ARCHIVE_PATH to a md:// URL.
"""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from typing import Any

import duckdb

from services.archive.backend import ArchiveBackend, ArchiveEvent
from config.logging import get_logger

logger = get_logger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS raw_pumpapi_events (
    seq         BIGINT,
    event_type  VARCHAR,
    received_at TIMESTAMPTZ NOT NULL,
    source      VARCHAR DEFAULT 'pumpapi',
    raw_json    VARCHAR NOT NULL
);
CREATE SEQUENCE IF NOT EXISTS _seq_pumpapi START 1;

CREATE TABLE IF NOT EXISTS raw_helius_events (
    seq         BIGINT,
    received_at TIMESTAMPTZ NOT NULL,
    source      VARCHAR DEFAULT 'helius',
    raw_json    VARCHAR NOT NULL
);
CREATE SEQUENCE IF NOT EXISTS _seq_helius START 1;

CREATE TABLE IF NOT EXISTS normalized_trades (
    signature    VARCHAR NOT NULL,
    token_mint   VARCHAR NOT NULL,
    wallet       VARCHAR,
    side         VARCHAR,
    sol_amount   DOUBLE,
    token_amount DOUBLE,
    timestamp    TIMESTAMPTZ,
    source       VARCHAR,
    inserted_at  TIMESTAMPTZ DEFAULT current_timestamp
);

CREATE TABLE IF NOT EXISTS tokens (
    mint         VARCHAR NOT NULL,
    name         VARCHAR,
    symbol       VARCHAR,
    creator      VARCHAR,
    created_at   TIMESTAMPTZ,
    metadata_uri VARCHAR,
    inserted_at  TIMESTAMPTZ DEFAULT current_timestamp
);

CREATE TABLE IF NOT EXISTS wallet_score_history (
    wallet          VARCHAR NOT NULL,
    composite_score DOUBLE,
    win_rate        DOUBLE,
    roi             DOUBLE,
    timing          DOUBLE,
    consistency     DOUBLE,
    scored_at       TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS signals (
    id          VARCHAR NOT NULL,
    token_mint  VARCHAR,
    signal_type VARCHAR,
    source_rule VARCHAR,
    confidence  DOUBLE,
    reason      VARCHAR,
    metadata    VARCHAR,
    is_active   BOOLEAN,
    fired_at    TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS signal_snapshots (
    signal_id           VARCHAR NOT NULL,
    token_mint          VARCHAR,
    fired_price_usd     DOUBLE,
    market_cap_usd      DOUBLE,
    liquidity_usd       DOUBLE,
    volume_1h_usd       DOUBLE,
    holders_count       INTEGER,
    smart_wallet_count  INTEGER,
    avg_wallet_score    DOUBLE,
    triggering_wallets  VARCHAR,
    signal_rule_version VARCHAR,
    created_at          TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS holder_snapshots (
    token_mint   VARCHAR NOT NULL,
    snapshot_at  TIMESTAMPTZ NOT NULL,
    top10_pct    DOUBLE,
    holder_count INTEGER,
    top_holders  VARCHAR,
    inserted_at  TIMESTAMPTZ DEFAULT current_timestamp
);

CREATE TABLE IF NOT EXISTS migrations (
    signature        VARCHAR,
    mint             VARCHAR NOT NULL,
    pool             VARCHAR,
    pool_id          VARCHAR,
    timestamp        TIMESTAMPTZ,
    quote_amount     DOUBLE,
    token_amount     DOUBLE,
    traders_involved INTEGER,
    price            DOUBLE,
    market_cap_quote DOUBLE,
    inserted_at      TIMESTAMPTZ DEFAULT current_timestamp
);
"""


def _extract_row(event: ArchiveEvent) -> tuple[str, dict[str, Any]]:
    """Map ArchiveEvent → (table_name, row_dict). Returns raw_pumpapi_events for unknown types."""
    p = event.payload
    et = event.event_type
    now = event.timestamp

    if et == "pumpapi_event":
        return "raw_pumpapi_events", {
            "event_type": p.get("event_type", "unknown"),
            "received_at": now,
            "source": "pumpapi",
            "raw_json": json.dumps(p.get("raw", p)),
        }
    if et == "helius_event":
        return "raw_helius_events", {
            "received_at": now,
            "source": "helius",
            "raw_json": json.dumps(p),
        }
    if et == "trade":
        return "normalized_trades", {
            "signature": p.get("signature"),
            "token_mint": p.get("token_mint"),
            "wallet": p.get("wallet"),
            "side": p.get("side"),
            "sol_amount": p.get("sol_amount"),
            "token_amount": p.get("token_amount"),
            "timestamp": p.get("timestamp"),
            "source": p.get("source", "unknown"),
            "inserted_at": now,
        }
    if et == "token":
        return "tokens", {
            "mint": p.get("mint"),
            "name": p.get("name"),
            "symbol": p.get("symbol"),
            "creator": p.get("creator"),
            "created_at": p.get("created_at"),
            "metadata_uri": p.get("metadata_uri"),
            "inserted_at": now,
        }
    if et == "wallet_score":
        return "wallet_score_history", {
            "wallet": p.get("wallet"),
            "composite_score": p.get("composite_score"),
            "win_rate": p.get("win_rate"),
            "roi": p.get("roi"),
            "timing": p.get("timing"),
            "consistency": p.get("consistency"),
            "scored_at": p.get("timestamp", now),
        }
    if et == "signal":
        return "signals", {
            "id": str(p.get("id", "")),
            "token_mint": p.get("token_mint"),
            "signal_type": p.get("signal_type"),
            "source_rule": p.get("source_rule"),
            "confidence": p.get("confidence"),
            "reason": p.get("reason"),
            "metadata": json.dumps(p.get("metadata")) if p.get("metadata") else None,
            "is_active": p.get("is_active", True),
            "fired_at": p.get("fired_at", now),
        }
    if et == "signal_snapshot":
        return "signal_snapshots", {
            "signal_id": str(p.get("signal_id", "")),
            "token_mint": p.get("token_mint"),
            "fired_price_usd": p.get("fired_price_usd"),
            "market_cap_usd": p.get("market_cap_usd"),
            "liquidity_usd": p.get("liquidity_usd"),
            "volume_1h_usd": p.get("volume_1h_usd"),
            "holders_count": p.get("holders_count"),
            "smart_wallet_count": p.get("smart_wallet_count"),
            "avg_wallet_score": p.get("avg_wallet_score"),
            "triggering_wallets": (
                json.dumps(p["triggering_wallets"]) if p.get("triggering_wallets") else None
            ),
            "signal_rule_version": p.get("signal_rule_version"),
            "created_at": p.get("created_at", now),
        }
    if et == "holder_snapshot":
        return "holder_snapshots", {
            "token_mint": p.get("token_mint"),
            "snapshot_at": p.get("snapshot_at", now),
            "top10_pct": p.get("top10_pct"),
            "holder_count": p.get("holder_count"),
            "top_holders": json.dumps(p["top_holders"]) if p.get("top_holders") else None,
            "inserted_at": now,
        }
    if et == "migration":
        return "migrations", {
            "signature": p.get("signature"),
            "mint": p.get("mint", ""),
            "pool": p.get("pool"),
            "pool_id": p.get("poolId") or p.get("pool_id"),
            "timestamp": p.get("timestamp"),
            "quote_amount": p.get("quoteAmount") or p.get("quote_amount"),
            "token_amount": p.get("tokenAmount") or p.get("token_amount"),
            "traders_involved": p.get("tradersInvolved") or p.get("traders_involved"),
            "price": p.get("price"),
            "market_cap_quote": p.get("marketCapQuote") or p.get("market_cap_quote"),
            "inserted_at": now,
        }
    # Unknown type — preserve raw
    return "raw_pumpapi_events", {
        "event_type": et,
        "received_at": now,
        "source": event.source,
        "raw_json": json.dumps(p),
    }


class DuckDBArchiveBackend(ArchiveBackend):
    def __init__(self, path: str):
        dir_ = os.path.dirname(os.path.abspath(path))
        os.makedirs(dir_, exist_ok=True)
        self._path = path
        self._lock = threading.Lock()
        self._conn = self._connect()
        self._init_schema()
        logger.info("DuckDB archive opened", path=path)

    def _connect(self) -> duckdb.DuckDBPyConnection:
        return duckdb.connect(self._path)

    def _init_schema(self) -> None:
        # Execute schema statements individually — DuckDB doesn't support multi-statement strings
        with self._lock:
            for stmt in _SCHEMA.strip().split(";"):
                stmt = stmt.strip()
                if stmt:
                    try:
                        self._conn.execute(stmt)
                    except Exception as e:
                        # Sequences may already exist — ignore
                        if "already exists" not in str(e).lower():
                            logger.warning("Archive schema statement failed", error=str(e), stmt=stmt[:80])

    def write_batch(self, events: list[ArchiveEvent]) -> None:
        if not events:
            return

        by_table: dict[str, list[dict[str, Any]]] = {}
        for event in events:
            try:
                table, row = _extract_row(event)
                by_table.setdefault(table, []).append(row)
            except Exception as e:
                logger.warning("Archive row extraction failed", event_type=event.event_type, error=str(e))

        with self._lock:
            for table, rows in by_table.items():
                if not rows:
                    continue
                try:
                    cols = list(rows[0].keys())
                    placeholders = ", ".join(["?" for _ in cols])
                    values = [[r.get(c) for c in cols] for r in rows]
                    self._conn.executemany(
                        f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({placeholders})",
                        values,
                    )
                except Exception as e:
                    logger.error("Archive batch insert failed", table=table, count=len(rows), error=str(e))
                    self._try_reconnect()

    def _try_reconnect(self) -> None:
        try:
            self._conn.close()
        except Exception:
            pass
        try:
            self._conn = self._connect()
            self._init_schema()
            logger.info("Archive DB reconnected")
        except Exception as e:
            logger.error("Archive DB reconnect failed", error=str(e))

    def get_db_size_mb(self) -> float:
        try:
            if os.path.exists(self._path):
                return os.path.getsize(self._path) / (1024 * 1024)
        except Exception:
            pass
        return 0.0

    def close(self) -> None:
        with self._lock:
            try:
                self._conn.close()
            except Exception:
                pass
