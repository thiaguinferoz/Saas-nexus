from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    app_name: str = "Nexus"
    app_secret_key: str = Field(min_length=32)
    database_url: str
    redis_url: str
    frontend_url: str = "http://localhost:3000"
    cookie_domain: str | None = None
    cookie_secure: bool = True
    access_token_expire_minutes: int = 30
    auto_create_tables: bool = False
    n8n_service_token: str | None = None
    billing_provider: str = "stripe"
    stripe_secret_key: str | None = None
    stripe_webhook_secret: str | None = None
    stripe_price_id: str | None = None
    ycloud_api_key: str | None = None
    ycloud_webhook_secret: str | None = None
    meta_app_id: str | None = None
    meta_embedded_signup_config_id: str | None = None
    n8n_internal_webhook_url: str = "http://n8n:5678/webhook/nexus-automation-v1"
    n8n_webhook_header_name: str = "X-Nexus-Token"
    workflow_schema_version: str = "1.0"
    redis_stream_prefix: str = "nexus"
    worker_max_attempts: int = 5
    worker_block_ms: int = 5000
    worker_claim_idle_ms: int = 60000
    outbox_poll_seconds: float = 1.0
    media_proxy_max_bytes: int = 25_000_000


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
