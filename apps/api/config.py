"""
RecoverFlow API — Application configuration.

Why this file exists:
  Centralises every environment-variable read into typed, validated Settings
  so that the rest of the codebase never calls os.getenv() directly and every
  missing variable is caught at startup rather than at runtime.
"""

from __future__ import annotations

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Database ----------------------------------------------------------
    database_url: str = (
        "postgresql+asyncpg://recoverflow:recoverflow@postgres:5432/recoverflow"
    )
    database_sync_url: str = (
        "postgresql://recoverflow:recoverflow@postgres:5432/recoverflow"
    )

    # --- Redis -------------------------------------------------------------
    redis_url: str = "redis://redis:6379/0"

    # --- API ---------------------------------------------------------------
    secret_key: str = "change_me_before_production"
    cors_origins: list[str] = ["http://localhost:3000"]
    environment: str = "development"
    log_level: str = "INFO"

    # --- Razorpay ----------------------------------------------------------
    razorpay_key_id: str = "rzp_test_REPLACE_ME"
    razorpay_key_secret: str = "REPLACE_ME"
    razorpay_webhook_secret: str = "REPLACE_ME"

    # --- LLM ---------------------------------------------------------------
    llm_provider: str = "mock"
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    gemini_api_key: str = ""
    llm_model: str = "gpt-4o-mini"

    # --- Feature Flags -----------------------------------------------------
    autonomous_actions_enabled: bool = False
    seed_synthetic_data: bool = False

    # --- Worker ------------------------------------------------------------
    worker_concurrency: int = 4

    # --- Frontend ----------------------------------------------------------
    next_public_api_url: str = "http://localhost:8000"
    internal_api_url: str = "http://api:8000"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _parse_cors(cls, v: str | list[str]) -> list[str]:
        """Parse CORS origins from a comma-separated string or list.

        Why: docker-compose passes env vars as plain strings; Pydantic needs
        to accept both representations to stay 12-factor compliant.
        """
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v


# Module-level singleton — imported everywhere as `from config import settings`.
settings = Settings()
