# MemeScope

Real-time behavioral intelligence engine for Solana memecoins. Tracks Top 10 holders and wallet behavior to generate early trading signals before the market reacts.

## What It Is

This is not a price tracker nor is it a chart app

It is a system that answers one question:

> Is this token worth entering **before** it moves?

It does that by watching **who holds**, **how they behave**, and **what they will do next** — using on-chain data before price reflects it.

## Core Features

- **Top 10 Holder Tracking** — continuous snapshots of holder composition, concentration, accumulation vs. dump patterns
- **Wallet Scoring (0–100)** — win rate, avg ROI, entry timing, hold duration, consistency
- **Smart Money Detection** — wallets that enter early and consistently profit
- **Cluster Detection** — identify multiple wallets controlled by the same entity
- **Pump.fun Early Detection** — new launches, first buyers, creator wallets
- **Signal Engine** — BUY / WATCH / AVOID signals with confidence scores and reasons
- **Real-time WebSocket stream** — signals pushed to frontend instantly
- **Worker Heartbeat Monitoring** — all 4 workers report liveness to Redis; health endpoint surfaces dead workers

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI (async), Python 3.12 |
| Database | PostgreSQL via Neon (SQLAlchemy asyncpg + Alembic migrations) |
| Queue / Cache | Redis Cloud |
| Blockchain | Helius RPC (`getSignaturesForAddress`, `getTransaction`) |
| Launches | PumpAPI WebSocket stream (`pumpapi.io`) |
| Price / Liquidity | Birdeye API |
| Frontend | React + Vite + TypeScript + TailwindCSS + shadcn/ui |
| Deployment | Render (backend + workers), Vercel (frontend) |
| Monitoring | Prometheus (`/metrics`) + Grafana Cloud |
| CI | GitHub Actions (backend unit tests + frontend type-check) |

## How It Works

```
PumpAPI detects launch
      ↓
Helius confirms transactions
      ↓
Parser → structured trade (wallet, token, side, amount, price)
      ↓
Wallet Intelligence → scores updated
      ↓
Top 10 Holder Engine → snapshot stored
      ↓
Signal Engine evaluates rules
      ↓
Signal published → WebSocket → Frontend
```

## Backend Structure

```
backend/
├── api/
│   ├── main.py              # FastAPI app, lifespan, CORS, rate limiting, Prometheus
│   ├── middleware/
│   │   └── rate_limit.py    # Redis-backed sliding window (200 req/min, in-memory fallback)
│   ├── routes/              # REST endpoints (signals, tokens, wallets, holders, stats, health)
│   └── websocket/           # Real-time signal stream (api_key auth via query param)
├── clients/
│   ├── helius_client.py     # Helius RPC wrapper (adaptive rate limiter)
│   ├── birdeye_client.py    # Price / liquidity fetcher (adaptive rate limiter)
│   └── pumpapi_client.py    # PumpAPI WebSocket listener (no API key required)
├── services/
│   ├── ingestion/           # Data collection (Helius, PumpAPI, Birdeye)
│   ├── parser/              # Raw tx → structured BUY/SELL events (Raydium, Meteora, Orca, Pump.fun)
│   ├── holders/             # Top 10 tracker, snapshots, diffs
│   ├── wallet_intelligence/ # Win rate, ROI, entry timing, behavior scoring
│   ├── clustering/          # Linked wallet detection
│   ├── signals/             # Signal engine + rules (smart entry, dump, cluster)
│   ├── pumpfun/             # Launch tracking, first buyers, creator wallets
│   └── scheduler/           # Periodic jobs (Top 10 refresh, score updates)
├── workers/
│   ├── parser_worker.py     # Consumes raw_tx_queue
│   ├── signal_worker.py     # Consumes signal_eval_queue
│   ├── holder_worker.py     # Consumes holder_update_queue
│   └── pumpfun_worker.py    # Consumes pumpfun_launch_queue
├── shared/
│   └── heartbeat.py         # Worker liveness (Redis keys, 90s TTL)
├── alembic/                 # Database migrations
├── models/                  # ORM (Wallet, Trade, Token, HolderSnapshot, Signal, Cluster)
├── repositories/            # Data access layer
├── schemas/                 # Pydantic request/response contracts
├── config/                  # Settings, constants, logging
├── core/                    # DB (SQLite-safe for tests), Redis, security
├── utils/                   # Adaptive rate limiter, helpers
├── scripts/                 # healthcheck, seed, init_db, e2e_flow
├── start_worker.py          # Worker entrypoint: python start_worker.py <name>
├── Dockerfile               # python:3.12-slim, PYTHONPATH=/app, HEALTHCHECK
└── tests/
    ├── conftest.py          # Sets SQLite env vars before any app imports
    ├── unit/                # 28 tests — no real DB, Redis, or external APIs needed
    └── integration/         # FastAPI TestClient against SQLite
```

## Frontend Structure

```
frontend/src/
├── pages/
│   ├── Index.tsx            # Main layout — resizable filter rail + feed + detail panel
│   ├── AlphaIntelView.tsx   # Wallet intelligence dashboard (real API data, skeleton loading)
│   ├── TokenPage.tsx        # Top 10 holder table, concentration bar
│   └── WalletPage.tsx       # Wallet profile, score breakdown, trade history
├── components/
│   ├── AlphaFeed.tsx        # Live signal list (REST poll 30s + WebSocket)
│   ├── FilterPanel.tsx      # Collapsible filter rail; collapsed icons open per-filter drawers
│   ├── TopBar.tsx           # Stats bar (polls /api/v1/stats every 60s)
│   ├── ActivityLog.tsx      # Real-time event log via WebSocket
│   ├── DetailPanel.tsx      # Signal detail drawer
│   └── SignalCard.tsx       # Individual signal row
└── lib/
    ├── api.ts               # Typed fetch + WebSocket connector (sends VITE_APP_API_KEY)
    └── mockData.ts          # Type definitions only (no mock data served to UI)
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Version ping |
| GET | `/api/v1/health` | DB, Redis, Helius, Birdeye + worker liveness |
| GET | `/api/v1/stats` | Active signals, tracked wallets, tokens scanned |
| GET | `/api/v1/signals` | List active signals |
| GET | `/api/v1/tokens` | List tracked tokens |
| GET | `/api/v1/holders/{mint}/top10` | Top 10 holders for a token |
| GET | `/api/v1/wallets/{address}` | Wallet profile |
| GET | `/api/v1/wallets/{address}/trades` | Wallet trade history |
| GET | `/metrics` | Prometheus metrics (requires `Authorization: Bearer <APP_API_KEY>`) |
| WS | `/ws/signals` | Real-time signal stream (pass `?api_key=` when APP_API_KEY is set) |

## Setup

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Mac/Linux
pip install -r requirements.txt
cp .env.example .env          # fill in keys
python -m pytest tests/unit/  # verify 28 tests pass (SQLite, no external services)
uvicorn api.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
cp .env.example .env          # set VITE_API_URL and VITE_APP_API_KEY
npm install
npm run dev
```

### Workers (local)

```bash
cd backend
python start_worker.py parser
python start_worker.py signal
python start_worker.py holder
python start_worker.py pumpfun
```

### Required Environment Variables

**Backend (`backend/.env`)**

```env
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/dbname
REDIS_URL=redis://localhost:6379/0
HELIUS_API_KEY=your_key
BIRDEYE_API_KEY=your_key
JWT_SECRET_KEY=minimum-32-character-secret-key
APP_ENV=development
APP_CORS_ORIGINS=["http://localhost:5173"]
APP_API_KEY=                  # optional — secures /metrics and WebSocket
```

**Frontend (`frontend/.env`)**

```env
VITE_API_URL=http://localhost:8000
VITE_APP_API_KEY=             # must match APP_API_KEY if set
```

> PumpAPI (`pumpapi.io`) requires no API key — connects via public WebSocket.

## Deployment

### Render (backend + workers)

`render.yaml` at repo root defines 1 web service + 4 worker services. Set all `sync: false` variables in the Render dashboard.

Web service start sequence:
```
alembic upgrade head → uvicorn api.main:app
```

Workers start via:
```
python start_worker.py <parser|signal|holder|pumpfun>
```

### Vercel (frontend)

- Root directory: `frontend`
- Build command: `npm run build`
- Output directory: `dist`
- Add `VITE_API_URL` and `VITE_APP_API_KEY` in Vercel environment settings

## Database Migrations

See [`backend/docs/migrations.md`](backend/docs/migrations.md) for the full workflow.

Quick reference:
```bash
cd backend
PYTHONPATH=. alembic revision --autogenerate -m "describe change"
PYTHONPATH=. alembic upgrade head
```

## Adaptive Rate Limiter

Free-tier API keys (Helius, Birdeye) use an adaptive limiter:

1. Runs at configured RPM (safe zone)
2. Every 3 days: probes at +10% for 24 hours
3. Probe passes cleanly → adopts as new production rate
4. 3+ rate limit errors → reverts to previous safe rate

State persists in `.rate_state.json` (gitignored).

## API Rate Limiting

All routes protected by Redis-backed sliding window (200 req/min per IP). Falls back to in-process rate limiting if Redis is unavailable. `/health`, `/api/v1/health`, and `/metrics` are exempt.

## Signals

| Signal | Trigger |
|--------|---------|
| `SMART_WALLET_ENTRY` | 3+ high-score wallets enter early |
| `TOP10_DUMP` | Top 10 holders reduce position significantly |
| `CLUSTER_ALERT` | Linked wallets control >30% of supply |

Each signal: confidence (HIGH/MEDIUM/LOW), action bias (ENTER/WATCH/AVOID), reasons list.

## Monitoring

`/metrics` exposes Prometheus data (request count, latency, status codes per route).

Point Grafana Cloud at `https://your-api.onrender.com/metrics` with header `Authorization: Bearer <APP_API_KEY>`. Import dashboard ID `17175` for a pre-built FastAPI view.

Worker liveness visible at `/api/v1/health` under the `workers` key — shows `ok`/`stale`/`dead` per worker.

## Tests

```bash
cd backend
python -m pytest tests/unit/ -q    # 28 tests, SQLite, no external services needed
python -m pytest tests/ -v         # full suite including integration
```

## CI

GitHub Actions runs on every push and PR to `main`:
- **Backend**: Python 3.12, installs deps, runs unit tests
- **Frontend**: Node 20, `npm ci`, TypeScript check, ESLint

## Healthcheck

```bash
cd backend
PYTHONPATH=. python scripts/healthcheck.py
```

Expected: all services green (DB, Redis, Helius, Birdeye).
