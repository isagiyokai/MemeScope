# PostgreSQL / Neon Data Management Guide

## Current Retention Policy

Holder snapshots older than 24 hours are deleted every 6 hours by the scheduler.

All other tables (tokens, wallets, trades, signals) are kept permanently — no purge runs on them.

---

## Option A — Change Retention Period (Keep More Data)

### Code change required

File: `backend/services/scheduler/jobs.py`

Find this line inside `_purge_old_snapshots()`:

```python
"DELETE FROM holder_snapshots WHERE snapshot_at < NOW() - INTERVAL '24 hours'"
```

Change `'24 hours'` to whatever you want to keep:

| Retention | Value to use |
|-----------|-------------|
| 24 hours (current) | `'24 hours'` |
| 3 days | `'3 days'` |
| 7 days | `'7 days'` |
| 30 days | `'30 days'` |
| Never delete | Delete the `_purge_old_snapshots` job entirely |

After editing, commit and push — Render redeploys automatically.

### Storage cost estimate

At current rate: ~374 MB per 24 hours of snapshots.

| Retention | Estimated storage |
|-----------|------------------|
| 24 hours  | ~374 MB |
| 7 days    | ~2.6 GB |
| 30 days   | ~11 GB |

Neon free tier is 512 MB total. Any retention beyond 24 hours requires a paid Neon plan.

### If you want to keep data but NOT run the purge yet

Comment out the scheduler registration in `start_scheduler()`:

```python
# _scheduler.add_job(
#     _purge_old_snapshots,
#     trigger=IntervalTrigger(hours=6),
#     id="purge_snapshots",
#     replace_existing=True,
#     max_instances=1,
# )
```

This stops all automatic deletion. You control deletion manually from the SQL editor.

---

## Option B — Manual Retention from Neon SQL Editor

No code change or redeploy needed. Go to Neon dashboard → SQL Editor.

### Delete snapshots older than N days manually

```sql
-- Keep last 7 days
DELETE FROM holder_snapshots
WHERE snapshot_at < NOW() - INTERVAL '7 days';

-- Keep last 30 days
DELETE FROM holder_snapshots
WHERE snapshot_at < NOW() - INTERVAL '30 days';

-- Delete everything (full reset)
TRUNCATE holder_snapshots;
```

### Reclaim space after large deletes

```sql
VACUUM FULL holder_snapshots;
```

### Check current storage usage

```sql
SELECT
  relname AS table,
  pg_size_pretty(pg_total_relation_size(relid)) AS total_size,
  n_live_tup AS row_count
FROM pg_stat_user_tables
ORDER BY pg_total_relation_size(relid) DESC;
```

---

## Option C — Migrate to New Neon Account or Database

### Step 1 — Export from old database

Run this on your local machine (requires PostgreSQL tools installed):

```cmd
pg_dump "postgresql://USER:PASSWORD@HOST/neondb?sslmode=require" ^
  --no-owner --no-acl --format=plain ^
  -f memescope_backup.sql
```

Replace `USER`, `PASSWORD`, `HOST` with values from your current Neon connection string.

To export only specific tables (e.g. exclude snapshots to save space):

```cmd
pg_dump "postgresql://USER:PASSWORD@HOST/neondb?sslmode=require" ^
  --no-owner --no-acl --format=plain ^
  -t tokens -t wallets -t trades -t signals -t clusters ^
  -f memescope_backup_no_snapshots.sql
```

### Step 2 — Create new Neon database

1. Go to neon.tech → New Project
2. Copy the new connection string (format: `postgresql://USER:PASS@HOST/neondb?sslmode=require&channel_binding=require`)

### Step 3 — Import into new database

```cmd
psql "postgresql://NEW_USER:NEW_PASSWORD@NEW_HOST/neondb?sslmode=require" ^
  -f memescope_backup.sql
```

### Step 4 — Run migrations on new database

```cmd
cd C:\Users\Administrator\Downloads\MemeScope\backend
venv\Scripts\activate
set DATABASE_URL=postgresql://NEW_USER:NEW_PASSWORD@NEW_HOST/neondb?sslmode=require
alembic upgrade head
```

### Step 5 — Update Render environment variables

1. Go to Render dashboard
2. Open **memescope-api** → Environment → `DATABASE_URL` → paste new connection string
3. Open **memescope-workers** → Environment → `DATABASE_URL` → paste same connection string
4. Both services will redeploy automatically

**Critical:** Both API and Workers must point to the same DATABASE_URL or they will see different data.

### Step 6 — Verify migration

Run in new Neon SQL editor:

```sql
SELECT
  (SELECT COUNT(*) FROM tokens)  AS tokens,
  (SELECT COUNT(*) FROM wallets) AS wallets,
  (SELECT COUNT(*) FROM trades)  AS trades,
  (SELECT COUNT(*) FROM signals) AS signals;
```

Compare counts against the old database to confirm data transferred correctly.

---

## What Gets Lost in a Migration

| Data | Recoverable? | Notes |
|------|-------------|-------|
| tokens | Yes | Re-ingested by PumpAPI stream within hours |
| wallets | Yes | Rebuilt from trades and PumpAPI events |
| trades | Yes | Re-fetched by Helius trade poller over time |
| signals | No | Historical signals are not regenerated |
| holder_snapshots | No | Real-time only, not reproducible |
| wallet composite_score | Partial | Scores reset to 0, rebuilt after trades re-accumulate |

Recommendation: always export `tokens`, `wallets`, `trades`, `signals` before migrating. Skip `holder_snapshots` — too large and regenerated automatically.

---

## Reminder — Tighten Signal Thresholds Later

Current cold-start settings (in `backend/config/constants.py`):

```python
SMART_WALLET_SCORE_THRESHOLD_COLD = 50   # production is 70
SMART_WALLET_MIN_COUNT_COLD = 2          # production is 3
```

Cold-start mode is active (`APP_SIGNAL_COLD_START_MODE=true` in Render env vars).

When wallet trade history matures (aim for 500+ wallets with score > 50):

1. Set `APP_SIGNAL_COLD_START_MODE=false` in Render env vars for both services
2. System automatically switches to production thresholds (score ≥ 70, 3 wallets)
3. No code change required

Documented in `backend/docs/remember_me.md`.
