"""Application configuration."""

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # App
    app_name: str = "ParallelDialer"
    debug: bool = False

    # Database
    database_url: str = "postgresql+asyncpg://parallel_dialer:dev_password@localhost:5432/parallel_dialer"

    # Redis
    redis_url: str = "redis://localhost:6379"

    # JWT
    secret_key: str = "dev-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # Twilio (mock by default)
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_phone_number: str = ""
    twilio_use_mock: bool = True

    # Dialer settings
    default_dial_ratio: float = 3.0
    max_abandon_rate: float = 0.03  # 3%
    amd_timeout_seconds: int = 30

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
