import os

# Set env vars before ANY application module is imported.
# core/db.py calls _get_engine() at module load; DATABASE_URL must be set first.
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_memescope.db")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-testing-only-min32!!")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("HELIUS_API_KEY", "test-helius-key")
os.environ.setdefault("BIRDEYE_API_KEY", "test-birdeye-key")
os.environ.setdefault("APP_ENV", "development")
