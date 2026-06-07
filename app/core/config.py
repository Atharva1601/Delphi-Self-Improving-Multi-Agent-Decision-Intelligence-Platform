"""
app/core/config.py
──────────────────
Central configuration powered by pydantic-settings.
All settings are loaded from environment variables / .env file.
"""
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ────────────────────────────────────────────────────────
    app_name: str = "Delphi"
    app_env: str = "development"          # development | staging | production
    app_version: str = "0.1.0"
    debug: bool = True
    log_level: str = "DEBUG"              # DEBUG | INFO | WARNING | ERROR

    # ── API ──────────────────────────────────────────────────────────────────
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_prefix: str = "/api/v1"

    # ── Database ─────────────────────────────────────────────────────────────
    database_url: str = Field(
        default="sqlite+aiosqlite:///./delphi.db",
        description="Async SQLAlchemy database URL.",
    )

    # ── LLM (Groq) ─────────────────────────────────────────────────────
    groq_api_key: str = Field(default="", description="Groq API key.")
    # Judge + Consensus: powerful, deliberate reasoning
    judge_model: str = "llama-3.3-70b-versatile"
    # Expert Agents + Router + Domain Specialist: fast parallel execution
    agent_model: str = "llama-3.1-8b-instant"

    # ── Reputation ────────────────────────────────────────────────────────────
    starting_reputation: float = 1000.0
    min_reputation: float = 700.0
    max_reputation: float = 1300.0
    reputation_k_factor: float = 16.0
    reflection_failure_threshold: float = 70.0
    reflection_success_threshold: float = 80.0
    recovery_threshold: float = 70.0
    recovery_lookback: int = 5
    reputation_recovery_threshold: float = 950.0

    # ── Security ─────────────────────────────────────────────────────────────

    secret_key: str = Field(
        default="change-me-in-production",
        description="Secret key for signing tokens.",
    )
    # Stored as comma-separated string in .env; split by property
    allowed_origins_raw: str = "http://localhost:3000,http://localhost:5173"

    @property
    def allowed_origins(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins_raw.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached singleton Settings instance."""
    return Settings()


# Convenience alias used throughout the codebase
settings = get_settings()
