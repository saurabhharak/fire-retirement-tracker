"""Application settings using pydantic-settings (12-factor compliant)."""

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    supabase_url: str
    supabase_key: str
    supabase_jwt_secret: str = ""  # Optional: only needed for legacy HS256 verification
    environment: str = "production"
    log_level: str = "INFO"
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:5174", "http://localhost:5175", "http://localhost:3000"]

    # Gold rate API keys (optional -- graceful degradation if missing)
    gold_api_key: str = ""           # Metals.dev API key  (env: GOLD_API_KEY)
    gold_api_key_fallback: str = ""  # GoldAPI.io fallback (env: GOLD_API_KEY_FALLBACK)

    @field_validator("cors_origins")
    @classmethod
    def no_wildcard_with_credentials(cls, v):
        if "*" in v:
            raise ValueError("Wildcard CORS origin not allowed with credentials")
        return v

    @property
    def is_development(self) -> bool:
        return self.environment == "development"


@lru_cache
def get_settings() -> Settings:
    return Settings()
