from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    bot_token: str = ""

    initial_admin_telegram_ids: str = ""
    admin_telegram_ids: str = ""

    session_secret: str = "dev-secret-change-in-production"
    session_ttl_minutes: int = 15
    session_absolute_ttl_hours: int = 8
    csrf_header_name: str = "X-CSRF-Token"

    database_url: str = "postgresql+asyncpg://tgscheduler:changeme@localhost:5432/tgscheduler"
    valkey_url: str = "redis://localhost:6379/0"

    cors_origins: str = "http://localhost:5173"

    api_reload: bool = False
    auth_date_max_age_seconds: int = 300
    rate_limit_auth_per_minute: int = 5
    rate_limit_api_per_minute: int = 60

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        if not v.startswith("postgresql"):
            raise ValueError("DATABASE_URL must be a PostgreSQL URL")
        return v

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def bootstrap_admin_ids(self) -> list[int]:
        raw = self.initial_admin_telegram_ids or self.admin_telegram_ids
        if not raw.strip():
            return []
        return [int(x.strip()) for x in raw.split(",") if x.strip()]


settings = Settings()
