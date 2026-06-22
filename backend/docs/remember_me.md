# MemeScope Signal Pipeline — Bootstrap Notes

## What We Did (2026-06-22)

### Problem
Signals = 0 despite 1034 wallets and 1521 tokens in DB.

### Root Causes Found

1. **`wallet_trades` was empty** — PumpAPI stream is create-only. No trades = no scoring.
2. **All 1034 wallets had `composite_score = NULL`** — Stubs were created without a score.
   The rescore job queries `WHERE composite_score >= 0.0`, which silently skips NULL rows.
   1034 wallets were permanently invisible to the scorer.
3. **`composite_score()` returned None if ANY component was missing** — Hard all-or-none gate.
   A wallet with BUY trades but no SELLs yet could never get a score.
4. **`SmartWalletEntryRule` thresholds too strict for cold start** — score ≥ 70, min 3 wallets.

### Fixes Applied

**Fix 1 — Data migration (immediate)**
- Migration `000000000003`: `UPDATE wallets SET composite_score = 0.0 WHERE composite_score IS NULL`
- Unblocks the rescore job for all existing wallets.

**Fix 2 — Trade ingestion (deployed same session)**
- New `TradePoller` service + scheduler job (`_refresh_trades`, 60s interval)
- Polls Helius `getSignaturesForAddress` for the 30 most recently launched tracked tokens
- Uses `last_trade_sig` cursor column on `tokens` to avoid re-fetching
- `parser_worker` now creates wallet stubs with `composite_score=0.0` after each trade stored

**Fix 3 — Cold-start signal thresholds**
- Added `APP_SIGNAL_COLD_START_MODE=true` config (default on)
- Cold-start: score threshold 50, min 2 wallets (vs production: 70, 3 wallets)
- Near-threshold events logged + `signals_near_threshold_total` counter

**Fix 4 — Partial composite scoring**
- `composite_score()` now scores wallets using whichever components are available
- Weights renormalized when components are missing
- Logs exactly which components were used / missing per wallet
- Metrics: `wallets_scored_total`, `wallets_unscorable_total`

### Files Changed
- `alembic/versions/000000000003_backfill_wallet_scores.py`
- `alembic/versions/000000000002_add_last_trade_sig.py`
- `models/token.py` — added `last_trade_sig` column
- `repositories/token_repo.py` — added `update_last_trade_sig()`
- `services/trades/trade_poller.py` — NEW
- `services/scheduler/jobs.py` — added `_refresh_trades()` job
- `workers/parser_worker.py` — wallet stub creation after trade save
- `services/metrics.py` — NEW simple in-memory counters
- `services/wallet_intelligence/behavior_analyzer.py` — partial scoring + metrics
- `services/signals/rules/smart_wallet_entry.py` — cold-start thresholds + near-threshold logging
- `config/constants.py` — cold-start threshold constants
- `config/settings.py` — `signal_cold_start_mode` setting

---

## TODO — Tighten Standards Later

When the pipeline has been running for 2–4 weeks with real trade data:

### 1. Disable cold-start mode
Set in Render env vars:
```
APP_SIGNAL_COLD_START_MODE=false
```
This restores production thresholds: score ≥ 70, min 3 wallets.

### 2. Fix `entry_timing_score` — it's a stub
Current implementation returns hardcoded `100.0` for any trade with a non-zero slot.
This inflates timing scores for every wallet. Replace with real relative-slot logic:
- Get token's first-ever trade slot from DB
- Score = 100 * (1 - (wallet_first_slot - token_first_slot) / time_window)
- Cap at 100, floor at 0

### 3. Add `HIGH_WINRATE_ACCUMULATION` rule
Fire when a wallet with win_rate ≥ 0.70 accumulates a token over 3+ separate buy orders.

### 4. Add `CLUSTER_ACCUMULATION` rule
Fire when 2+ wallets in the same cluster all buy the same token within 30 minutes.
(ClusterDetector must be generating cluster_ids first — check `wallets.cluster_id` is populated.)

### 5. Add `TOP10_CONVERGENCE` rule
Fire when 3+ top-10 holder wallets also appear in wallet_trades as recent buyers
(i.e., top holders and smart money are both in the same token).

### 6. Persist metrics to Redis
Current `services/metrics.py` resets on deploy. For production visibility, write counters
to Redis with TTL and expose via `/metrics` endpoint in the API.

### 7. Review `MIN_TRADES_FOR_SCORE = 3`
Currently requires 3 distinct tokens before `consistency_score` is computed.
On cold start, most wallets have 1–2 tokens. Consider lowering to 2 during cold-start mode.

---

## Signal Health Check Queries

Run these against Neon to spot-check pipeline state:

```sql
-- How many wallets have real scores vs zero stubs
SELECT
  COUNT(*) FILTER (WHERE composite_score IS NULL) AS null_score,
  COUNT(*) FILTER (WHERE composite_score = 0.0)  AS zero_stub,
  COUNT(*) FILTER (WHERE composite_score > 0.0 AND composite_score < 50) AS low,
  COUNT(*) FILTER (WHERE composite_score >= 50 AND composite_score < 70) AS medium,
  COUNT(*) FILTER (WHERE composite_score >= 70) AS high
FROM wallets;

-- Trade ingestion working?
SELECT COUNT(*), MIN(timestamp), MAX(timestamp) FROM wallet_trades;

-- Which tokens have the most trades (most active)
SELECT token_mint, COUNT(*) as trades
FROM wallet_trades
GROUP BY token_mint
ORDER BY trades DESC
LIMIT 10;

-- Signals generated so far
SELECT signal_type, source_rule, COUNT(*) FROM signals GROUP BY signal_type, source_rule;
```
