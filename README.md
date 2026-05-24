# MemeScope

Real-time behavioral intelligence engine for Solana memecoins. Tracks Top 10 holders and wallet behavior to generate early trading signals before the market reacts.

## What It Is

Not a chart app. Not a price tracker.

A system that answers one question:

> Is this token worth entering **before** it moves?

It does that by watching **who holds**, **how they behave**, and **what they will do next** — using on-chain data before price reflects it.

## Core Features

- **Top 10 Holder Tracking** — continuous snapshots of holder composition, concentration, accumulation vs. dump patterns
- **Wallet Scoring (0–100)** — win rate, avg ROI, entry timing, hold duration, consistency
- **Smart Money Detection** — wallets that enter early and consistently profit
- **Cluster Detection** — identify multiple wallets controlled by the same entity
- **Pump.fun Early Detection** — new launches, first buyers, creator wallets
- **Signal Engine** — BUY / WATCH / AVOID signals with confidence scores and reasons

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI (async), Python 3.11+ |
| Database | PostgreSQL via Neon (SQLAlchemy asyncpg) |
| Queue / Cache | Redis |
| Blockchain | Helius RPC (`getSignaturesForAddress`, `getTransaction`) |
| Launches | PumpAPI WebSocket stream (`pumpapi.io`) |
| Price / Liquidity | Birdeye API |
| Frontend | React + Vite + TypeScript + TailwindCSS + shadcn/ui |
| Deployment | Render (backend), Neon (DB), Redis Cloud |

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
│   ├── main.py              # FastAPI app, lifespan, CORS, routes
│   ├── routes/              # REST endpoints (signals, tokens, wallets, holders, stats, health)
│   └── websocket/           # Real-time signal stream
├── clients/
│   ├── helius_client.py     # Helius RPC wrapper (adaptive rate limiter)
│   ├── birdeye_client.py    # Price / liquidity fetcher (adaptive rate limiter)
│   └── pumpapi_client.py    # PumpAPI WebSocket listener (no API key required)
├── services/
│   ├── ingestion/           # Data collection (Helius, PumpAPI, Birdeye)
│   ├── parser/              # Raw tx → structured BUY/SELL events
│   ├── holders/             # Top 10 tracker, snapshots, diffs
│   ├── wallet_intelligence/ # Win rate, ROI, entry timing, behavior scoring
│   ├── clustering/          # Linked wallet detection
│   ├── signals/             # Signal engine + rules (smart entry, dump, cluster)
│   ├── pumpfun/             # Launch tracking, first buyers, creator wallets
│   └── scheduler/           # Periodic jobs (Top 10 refresh, score updates)
├── workers/                 # Redis queue consumers (parser, signal, holder)
├── models/                  # ORM (Wallet, Trade, Token, HolderSnapshot, Signal, Cluster)
├── repositories/            # Data access layer
├── schemas/                 # Pydantic request/response contracts
├── config/                  # Settings, constants, logging
├── core/                    # DB, Redis, security
├── utils/                   # Rate limiter (adaptive), helpers
├── scripts/                 # healthcheck, seed, init_db, e2e_flow
└── tests/                   # Unit + integration
```

## Frontend Structure

```
frontend/src/
├── pages/
│   ├── Index.tsx            # Main dashboard (signal feed + detail panel)
│   ├── TokenPage.tsx        # Top 10 holder table, concentration bar
│   ├── WalletPage.tsx       # Wallet profile, score breakdown, trade history
│   └── AlphaIntelPage.tsx   # Alpha intelligence feed
├── components/
│   ├── AlphaFeed.tsx        # Live signal list (REST poll 30s + WebSocket)
│   ├── TopBar.tsx           # Stats bar (polls /api/v1/stats every 60s)
│   ├── ActivityLog.tsx      # Real-time event log via WebSocket
│   ├── DetailPanel.tsx      # Signal detail drawer
│   └── SignalCard.tsx       # Individual signal row
└── lib/
    ├── api.ts               # Typed fetch functions + WebSocket connector
    └── mockData.ts          # Type definitions only (no mock data)
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Version ping |
| GET | `/api/v1/health` | Per-service status (DB, Redis, Helius, Birdeye) |
| GET | `/api/v1/stats` | Active signals, tracked wallets, tokens scanned |
| GET | `/api/v1/signals` | List active signals |
| GET | `/api/v1/tokens` | List tracked tokens |
| GET | `/api/v1/holders/{mint}/top10` | Top 10 holders for a token |
| GET | `/api/v1/wallets/{address}` | Wallet profile |
| GET | `/api/v1/wallets/{address}/trades` | Wallet trade history |
| WS | `/ws/signals` | Real-time signal stream |

## Setup

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env       # fill in keys
python scripts/init_db.py
uvicorn api.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
cp .env.example .env       # set VITE_API_URL=http://localhost:8000
npm install
npm run dev
```

### Required Environment Variables

```env
# Database
DATABASE_URL=postgresql+asyncpg://...

# Redis
REDIS_URL=redis://...

# Helius
HELIUS_API_KEY=your_key
HELIUS_RPC_URL=https://mainnet.helius-rpc.com/?api-key=your_key

# Birdeye
BIRDEYE_API_KEY=your_key

# JWT
SECRET_KEY=your_secret
```

> PumpAPI (`pumpapi.io`) requires no API key — connects via public WebSocket.

## Adaptive Rate Limiter

Free-tier API keys (Helius, Birdeye) use an adaptive limiter that:

1. Runs at configured RPM (safe zone)
2. Every 3 days: probes at +10% for 24 hours
3. If probe passes cleanly → adopts as new production rate
4. If 3+ rate limit errors → reverts to previous safe rate

State persists in `.rate_state.json` (gitignored). No crashes.

## Signals

Three built-in rules:

| Signal | Trigger |
|--------|---------|
| `SMART_WALLET_ENTRY` | 3+ high-score wallets enter early |
| `TOP10_DUMP` | Top 10 holders reduce position significantly |
| `CLUSTER_ALERT` | Linked wallets control >30% of supply |

Each signal carries: confidence (HIGH/MEDIUM/LOW), action bias (ENTER/WATCH/AVOID), reasons list.

## Healthcheck

```bash
cd backend
PYTHONPATH=. python scripts/healthcheck.py
```

Expected: all services green (DB, Redis, Helius, Birdeye).

## Tests

```bash
cd backend
python -m pytest tests/ -v
```
