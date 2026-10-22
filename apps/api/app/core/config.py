from functools import lru_cache
from typing import Literal

from pydantic import AnyHttpUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "DentalVoice AI"
    app_env: Literal["development", "production", "test"] = "development"
    api_v1_prefix: str = "/api/v1"
    secret_key: str = Field(default="change-me-in-dev")
    jwt_secret_key: str = Field(default="change-me-in-dev")
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24
    database_url: str = "postgresql+psycopg://dentalvoice:supersecret@postgres:5432/dentalvoice"
    redis_url: str = "redis://redis:6379/0"
    allowed_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    demo_admin_email: str = "admin@harbordentaldemo.local"
    demo_admin_password: str = "AdminPass123!"
    retell_api_key: str = "dev-retell-key"
    retell_webhook_secret: str = "dev-retell-webhook-secret"
    retell_agent_id: str = "agent_demo_001"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def allowed_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
