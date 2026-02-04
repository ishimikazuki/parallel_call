"""Application configuration."""

from functools import lru_cache

from pydantic import field_validator
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

    # CORS
    cors_origins: list[str] = ["http://localhost:5173"]
    cors_origin_regex: str | None = None

    # Public URL (for webhooks/signature validation)
    public_base_url: str | None = None

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
    twilio_api_key_sid: str = ""
    twilio_api_key_secret: str = ""
    twilio_app_sid: str = ""
    twilio_validate_signature: bool = False

    # Dialer settings
    default_dial_ratio: float = 3.0
    max_abandon_rate: float = 0.03  # 3%
    amd_timeout_seconds: int = 30

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, list):
            return value
        if not value:
            return []
        if value.strip() == "*":
            return ["*"]
        return [item.strip() for item in value.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
