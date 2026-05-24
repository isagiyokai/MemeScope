# MemeScope Backend — Master Todo & Build Tracker

> **Philosophy:** Raw blockchain data -> structured trades -> wallet profiles -> holder intelligence -> actionable signals.
> **Last Updated:** 2026-05-20 (UTC)

---

## COMPLETED

- [x] Project scaffold created (folders, empty files, Docker/config stubs)
- [x] `.env` configured with API keys and infrastructure URLs
  - `HELIUS_API_KEY`
  - `BIRDEYE_API_KEY`
  - `DATABASE_URL` (Neon PostgreSQL)
  - `REDIS_URL` (Redis Cloud)
  - `JWT_SECRET_KEY`
- [x] `requirements.txt` — all dependencies listed (FastAPI, SQLAlchemy async, Redis, httpx, solana, structlog, tenacity, etc.)
- [x] `config/settings.py` — Pydantic Settings with nested groups (database, redis, helius, birdeye, jwt, app, pumpapi)
- [x] `config/constants.py` — Solana program IDs, WSOL, score thresholds, signal confidence levels
- [x] `config/logging.py` — structured JSON logging via structlog
- [x] `core/db.py` — async SQLAlchemy engine + session factory for Neon (`postgresql+asyncpg://`)
- [x] `core/redis.py` — async Redis client wrapper with health check
- [x] `core/security.py` — JWT create/decode + bcrypt password hashing
- [x] SQLAlchemy Models (`models/`)
  - `token.py`, `wallet.py`, `trade.py`, `holder_snapshot.py`, `signal.py`, `cluster.py`
- [x] `alembic.ini` + async `alembic/env.py` + initial migration `000000000001_initial.py`
- [x] Pydantic Schemas (`schemas/`)
  - token, wallet, trade, holder, signal, cluster schemas + `__init__.py`
- [x] Repositories (`repositories/`)
  - wallet_repo, trade_repo, token_repo, holder_repo, signal_repo, cluster_repo
- [x] External Clients (`clients/`)
  - `helius_client.py` — RPC methods with tenacity retries
  - `birdeye_client.py` — REST API with retries
  - `pumpapi_client.py` — no key needed, latest launches + first buyers + creator
- [x] Ingestion Layer (`services/ingestion/`)
  - `ingestion.py` — HeliusListener, PumpfunListener, PriceFetcher unified module
- [x] Parser (`services/parser/`)
  - `swap_decoder.py` — Raydium, Jupiter, Pump.fun heuristics
  - `transfer_parser.py` — SPL transfer detection
  - `event_normalizer.py` — unified BUY/SELL/TRANSFER event format
- [x] Holders Engine (`services/holders/`)
  - `top10_tracker.py` — fetch & store Top 10 via Helius
  - `holder_snapshot.py` — snapshot persistence service
  - `holder_diff.py` — accumulation/distribution diff engine
- [x] Wallet Intelligence (`services/wallet_intelligence/`)
  - `wallet_profiler.py` — profile from trade history
  - `winrate_calculator.py` — profitable token ratio
  - `roi_engine.py` — realized/unrealized avg ROI
  - `behavior_analyzer.py` — timing + consistency + composite score 0-100
- [x] Clustering (`services/clustering/`)
  - `cluster_detector.py` — token overlap + timing union-find clustering
  - `funding_tracker.py` — common funding source detection stub
  - `pattern_matcher.py` — cosine-similarity activity vector clustering
- [x] Pump.fun (`services/pumpfun/`)
  - `launch_tracker.py` — ingest launches, persist tokens, persist first buyers + creators
  - `first_buyers.py` — dedicated first-buyer ingestion
  - `creator_tracker.py` — creator wallet tagging
- [x] Signal Engine (`services/signals/`)
  - `signal_engine.py` — master coordinator + deduplication
  - `signal_publisher.py` — Redis pub/sub publish for WebSocket
  - `smart_wallet_entry.py` — rule: N high-WR wallets entered recently
  - `top10_dump.py` — rule: Top 10 net reduced by threshold
  - `cluster_alert.py` — rule: cluster concentration in Top 10
- [x] Scheduler (`services/scheduler/`)
  - `jobs.py` — APScheduler with periodic holder refresh, wallet rescoring, signal evaluation, cluster detection, Pump.fun ingestion
  - `pumpfun_job.py` — enqueue Pump.fun launches from PumpAPI to Redis
- [x] Workers (`workers/`)
  - `parser_worker.py` — consumes `raw_tx_queue`, stores trades, enqueues signals
  - `signal_worker.py` — evaluates rules per token from `signal_eval_queue`
  - `holder_worker.py` — periodic Top 10 refresh + queue-driven updates
  - `pumpfun_worker.py` — consumes `pumpfun_launch_queue`, enqueues downstream jobs
- [x] FastAPI App (`api/`)
  - `main.py` — app factory, lifespan, CORS, health endpoint, route registration, scheduler start/shutdown
  - `dependencies.py` — DB + Redis FastAPI dependencies
  - `routes/tokens.py` — list, get, create token tracking
  - `routes/wallets.py` — profile, trades, tokens
  - `routes/holders.py` — top10, history, changes
  - `routes/signals.py` — list, filter, token-specific signals
  - `routes/clusters.py` — list, get, detect clusters
  - `websocket/signal_stream.py` — Redis pub/sub bridged to WebSocket
- [x] `utils/helpers.py` — formatting, address validation, math helpers
- [x] Scripts (`scripts/`)
  - `init_db.py` — create tables + Redis check
  - `healthcheck.py` — DB, Redis, Helius, Birdeye connectivity
  - `seed_data.py` — seed WSOL/USDC tokens and known wallets
  - `backfill_wallets.py` — recompute scores for all wallets
  - `reprocess_trades.py` — re-run parser on unparsed trades
- [x] `Dockerfile` + `docker-compose.yml` — runnable backend + 4 workers + Redis + Postgres
- [x] `README.md` — setup, architecture, worker run commands
- [x] `.gitignore`
- [x] Empty `__init__.py` files filled with minimal exports (services, core, api, scheduler, ingestion, clustering, pumpfun)
- [x] Bogus nested directories removed (`services/api/ingestion/...`, `models/repositories/...`, `migrations/`)
- [x] Test stubs created (`tests/unit/`, `tests/integration/`)
- [x] Documentation stubs written (`docs/api-spec.md`, `docs/architecture.md`, `docs/deployment.md`, `docs/runbooks.md`)

---

## PENDING — VERIFY / TEST / ITERATE

### Environment Validation
- [x] Install dependencies (`pip install -r requirements.txt`)
- [x] Run `python scripts/init_db.py` -> verify Neon tables created
- [x] Run `python scripts/healthcheck.py` -> verify all green

### API Smoke Test
- [x] `uvicorn api.main:app --reload` boots without errors
- [x] `GET /health` returns OK
- [x] `POST /api/v1/tokens` adds a token
- [x] `GET /api/v1/tokens` lists tracked tokens
- [x] `GET /api/v1/holders/{mint}/top10` returns holder data — 200 + 10 WIF holders confirmed
- [x] `GET /api/v1/signals` returns signals — 200 + empty list (no trades yet, expected)

### End-to-End Data Flow
- [x] Helius listener enqueues raw tx -> parser_worker parses -> trade stored
- [x] Signal worker evaluates stored trades -> signal generated (0 signals expected at this stage — rules need real trading history)
- [x] Holder worker refreshes Top 10 -> snapshots stored (verified with WIF/dogwifhat, 10 snapshots via Helius)
- [x] Pump.fun worker ingests launch -> token + first buyers persisted
- [x] PumpAPI WebSocket stream reachable (wss://stream.pumpapi.io/ — real-time events confirmed)

### Known Gaps / Future Work

- [x] Parser accuracy improved — uiAmount (float) replaces raw amount (lamport string), Meteora/Orca dispatched, multi-account same-mint balances summed, PumpAPI _pumpapi trade events handled in normalizer. Real-tx production tuning ongoing.
- [x] PumpAPI endpoint URL verified — PumpAPI is a WebSocket stream (wss://stream.pumpapi.io/), NOT a REST API. Client rewritten to use WebSocket. Event types: create, trade, transfer, migration.
- [x] Historical backfill from Helius — implemented in `scripts/backfill_history.py`; paginates `getSignaturesForAddress` with `before` cursor (up to 20 pages × 100 sigs per wallet), filters by `--days` cutoff (default 30), skips already-stored signatures. Run: `PYTHONPATH=. python scripts/backfill_history.py --days 30`
- [x] Rate limit / quota monitoring for Helius & Birdeye — implemented `utils/rate_limiter.py` (token-bucket with `asyncio.Lock`); Birdeye wired at 60 RPM, Helius configurable via `HELIUS_RPM` env var (default 600 = 10 RPS). `limiter.stats` exposes `rpm`, `total_requests`, `avg_wait_ms`.
- [ ] Signal WebSocket publishing currently reads from pub/sub; signal_worker publishes via `publish_signal()` — functional; no action required
- [x] Unit tests replaced — 44 unit tests (parser, wallet intelligence, signals, rate limiter ×7, funding tracker ×9) + 11 integration tests (API routes, workers) all passing
- [x] Cluster funding detection — `services/clustering/funding_tracker.py` fully implemented; parses Helius `jsonParsed` system-program Transfer instructions to find SOL funders per wallet, counts shared funders across cluster wallets, persists `common_funding_source` when ≥ max(2, n//2) wallets share a funder. `FundingTracker.run()` processes all clusters with ≥2 wallets.
- [x] Pump.fun listener mint extraction heuristic resolved — PumpAPI WebSocket delivers structured `create` events with `mint` field directly; heuristic no longer needed
- [x] Add `/api/v1/health` endpoint with per-service status (DB, Redis, external APIs) — implemented in `api/routes/health.py`, all services confirmed green

---

## COMPLETION CRITERIA ("Reasonable Workable State")

Before production use, confirm:
- [x] `scripts/healthcheck.py` passes (DB, Redis, Helius, Birdeye all green)
- [x] `scripts/init_db.py` creates tables without error
- [x] FastAPI boots and basic routes respond
- [x] At least one token can be added and Top 10 snapshot retrieved
- [x] Dockerfile builds successfully — `memescope-backend:test` image built and verified

---

Last Updated: 2026-05-20 (UTC)
