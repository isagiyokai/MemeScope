# MemeScope Backend

Behavioral intelligence engine for memecoin Top 10 holder analysis and wallet scoring.

## Quick Start

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Ensure `.env` is present with:
   - `DATABASE_URL`
   - `REDIS_URL`
   - `HELIUS_API_KEY`
   - `BIRDEYE_API_KEY`
   - `JWT_SECRET_KEY`

3. Initialize database tables:
   ```bash
   python scripts/init_db.py
   ```

4. Run health check:
   ```bash
   python scripts/healthcheck.py
   ```

5. Start the API:
   ```bash
   uvicorn api.main:app --reload
   ```

## Architecture

```
Raw blockchain data (Helius)
  -> Ingestion / Parser
  -> Trade events stored in PostgreSQL (Neon)
  -> Wallet Intelligence Engine scores wallets
  -> Top 10 Holder Tracker snapshots supply concentration
  -> Signal Engine evaluates rules (smart entry, dump, cluster)
  -> REST API + WebSocket serves signals to frontend
```

## Key Components

- `services/parser/` � Swap/transfer decoding (Raydium, Jupiter, Pump.fun)
- `services/holders/` � Top 10 holder snapshotting and diffing
- `services/wallet_intelligence/` � Win rate, ROI, timing, composite scoring
- `services/signals/` � Rule-based signal generation
- `api/routes/` � FastAPI endpoints for tokens, wallets, holders, signals
- `workers/` � Redis-backed background processors

## Workers

Run parser worker:
```bash
python -c "import asyncio; from workers.parser_worker import run_parser_worker; asyncio.run(run_parser_worker())"
```

Run signal worker:
```bash
python -c "import asyncio; from workers.signal_worker import run_signal_worker; asyncio.run(run_signal_worker())"
```

Run holder refresh worker:
```bash
python -c "import asyncio; from workers.holder_worker import run_holder_worker; asyncio.run(run_holder_worker())"
```

## Deployment

Build and run with Docker Compose:
```bash
docker-compose up --build
```

## Environment

| Variable | Description |
|----------|-------------|
| `DATABASE_URL`   | Neon PostgreSQL connection string |
| `REDIS_URL`      | Redis Cloud connection string     |
| `HELIUS_API_KEY` | Helius RPC API key                |
| `BIRDEYE_API_KEY`| Birdeye API key                   |
| `JWT_SECRET_KEY` | Secret for JWT signing            |