import json
import os
from functools import lru_cache
from typing import Optional

from dotenv import dotenv_values
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    url: str = ""
    pool_size: int = 10
    max_overflow: int = 20
    echo: bool = False

    model_config = SettingsConfigDict(env_prefix="DB_")


class RedisSettings(BaseSettings):
    url: str = ""
    db: int = 0
    decode_responses: bool = True

    model_config = SettingsConfigDict(env_prefix="REDIS_")


class HeliusSettings(BaseSettings):
    api_key: str = ""
    rpc_url: str = "https://mainnet.helius-rpc.com/?api-key={api_key}"
    webhook_url: Optional[str] = None
    request_timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0
    rpm: int = 600

    model_config = SettingsConfigDict(env_prefix="HELIUS_")

    def get_rpc_url(self) -> str:
        return self.rpc_url.format(api_key=self.api_key)


class BirdeyeSettings(BaseSettings):
    api_key: str = ""
    base_url: str = "https://public-api.birdeye.so"
    request_timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0

    model_config = SettingsConfigDict(env_prefix="BIRDEYE_")


class JWTSettings(BaseSettings):
    secret_key: str = ""
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60  # 1 hour — was 7 days (security fix)

    model_config = SettingsConfigDict(env_prefix="JWT_")


class AppSettings(BaseSettings):
    name: str = "MemeScope"
    version: str = "0.1.0"
    debug: bool = False
    env: str = "development"
    log_level: str = "INFO"
    # Stored as str so pydantic-settings never JSON-decodes an empty env var.
    # Use get_cors_origins() to get the parsed list.
    cors_origins: str = '["http://localhost:5173","http://localhost:3000"]'
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = False
    api_key: str = ""  # Set APP_API_KEY to require key on write endpoints + WebSocket

    model_config = SettingsConfigDict(env_prefix="APP_")

    def get_cors_origins(self) -> list[str]:
        v = self.cors_origins.strip()
        if not v:
            return ["http://localhost:5173", "http://localhost:3000"]
        if v.startswith("["):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                pass
        return [o.strip() for o in v.split(",") if o.strip()]


class PumpAPISettings(BaseSettings):
    stream_url: str = "wss://stream.pumpapi.io/"

    model_config = SettingsConfigDict(env_prefix="PUMPAPI_")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database: DatabaseSettings = DatabaseSettings()
    redis: RedisSettings = RedisSettings()
    helius: HeliusSettings = HeliusSettings()
    birdeye: BirdeyeSettings = BirdeyeSettings()
    jwt: JWTSettings = JWTSettings()
    app: AppSettings = AppSettings()
    pumpapi: PumpAPISettings = PumpAPISettings()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env")
        # .env values are the base — real environment variables take precedence
        try:
            dotenv_env = dotenv_values(env_path)
        except Exception:
            dotenv_env = {}
        dotenv_env.update(os.environ)  # real env vars win over .env
        env = dotenv_env
        if not self.database.url:
            self.database.url = env.get("DATABASE_URL", "")
        if not self.redis.url:
            self.redis.url = env.get("REDIS_URL", "")
        if not self.helius.api_key:
            self.helius.api_key = env.get("HELIUS_API_KEY", "")
        if not self.birdeye.api_key:
            self.birdeye.api_key = env.get("BIRDEYE_API_KEY", "")
        if not self.jwt.secret_key:
            self.jwt.secret_key = env.get("JWT_SECRET_KEY", "")
        if not self.app.api_key:
            self.app.api_key = env.get("APP_API_KEY", "")

    def validate_security(self) -> None:
        """Call at startup. Raises if critical security config is missing."""
        errors = []
        if not self.jwt.secret_key:
            errors.append("JWT_SECRET_KEY is not set — token signing is disabled")
        elif len(self.jwt.secret_key) < 32:
            errors.append("JWT_SECRET_KEY is too short (minimum 32 characters)")
        if self.app.env != "development" and "*" in self.app.get_cors_origins():
            errors.append("APP_CORS_ORIGINS must not be '*' in non-development environments")
        if errors:
            import warnings
            for e in errors:
                warnings.warn(f"[MemeScope security] {e}", stacklevel=2)


@lru_cache
def get_settings() -> Settings:
    return Settings()
