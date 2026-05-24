# Database Migrations

Alembic manages all schema changes. Every model change must have a migration before it reaches production.

## Workflow

### 1. Make your model change

Edit or add a file in `backend/models/`. Example — adding a column to `Token`:

```python
# models/token.py
market_cap_usd = Column(Float, nullable=True)
```

### 2. Generate the migration

From `backend/`:

```bash
PYTHONPATH=. alembic revision --autogenerate -m "add market_cap_usd to tokens"
```

This creates `alembic/versions/<hash>_add_market_cap_usd_to_tokens.py`. **Always review it** — autogenerate misses some things (check constraints, custom types, renaming).

### 3. Review the generated file

```bash
# alembic/versions/<hash>_add_market_cap_usd_to_tokens.py
def upgrade() -> None:
    op.add_column('tokens', sa.Column('market_cap_usd', sa.Float(), nullable=True))

def downgrade() -> None:
    op.drop_column('tokens', 'market_cap_usd')
```

Verify:
- `upgrade()` does what you intended
- `downgrade()` cleanly reverses it
- No destructive ops without a `nullable=True` or default on existing rows

### 4. Test locally

```bash
# Apply
PYTHONPATH=. alembic upgrade head

# Check current revision
PYTHONPATH=. alembic current

# Roll back one step if needed
PYTHONPATH=. alembic downgrade -1
```

### 5. Deploy

On Render, `alembic upgrade head` runs automatically as part of the web service `startCommand` before uvicorn starts. Workers deploy separately and do not run migrations.

---

## Common commands

| Command | What it does |
|---------|-------------|
| `alembic revision --autogenerate -m "..."` | Generate migration from model diff |
| `alembic upgrade head` | Apply all pending migrations |
| `alembic downgrade -1` | Roll back one migration |
| `alembic current` | Show current DB revision |
| `alembic history` | Show full migration history |
| `alembic show head` | Show what HEAD migration contains |

## Rules

- Never edit a migration that has already been applied to production.
- If you need to fix a mistake in a deployed migration, write a new migration that corrects it.
- All migrations must have a working `downgrade()` — no `pass`.
- Columns added to existing tables must be `nullable=True` or have a server-side `default` to avoid locking a live table.
