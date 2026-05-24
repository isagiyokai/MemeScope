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
    rpm: int = 600  # 10 RPS sustained (developer plan); set lower via HELIUS_RPM for free tier

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
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 days

    model_config = SettingsConfigDict(env_prefix="JWT_")


class AppSettings(BaseSettings):
    name: str = "MemeScope"
    version: str = "0.1.0"
    debug: bool = False
    env: str = "development"
    log_level: str = "INFO"
    cors_origins: list[str] = ["*"]  # override via APP_CORS_ORIGINS in production
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = False

    model_config = SettingsConfigDict(env_prefix="APP_")


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
        # Load .env explicitly so values are always available even if env_file parsing is subtle
        env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env")
        env = dict(os.environ)
        try:
            dotenv_env = dotenv_values(env_path)
        except Exception:
            dotenv_env = {}
        env.update(dotenv_env)
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


@lru_cache
def get_settings() -> Settings:
    return Settings()
