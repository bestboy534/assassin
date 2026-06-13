from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

Environment = Literal["local", "test", "staging", "production"]
QueueBackend = Literal["memory", "redis"]
StorageBackend = Literal["local", "s3"]
PaymentProviderBackend = Literal["fake", "stripe_issuing"]
BillingProviderBackend = Literal["fake", "stripe"]
IntegrationProviderBackend = Literal["fake_identity"]


class Settings(BaseSettings):
    app_environment: Environment = "local"
    app_name: str = "SaaS Assassin API"
    app_version: str = "0.2.0"
    api_v1_prefix: str = "/api/v1"

    openai_api_key: SecretStr = SecretStr("")
    openai_base_url: str = ""
    model_name: str = "gpt-4o-mini"
    use_llm: bool = False

    allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    save_raw_billing_text: bool = False
    log_level: str = "info"
    max_input_chars: int = 30000

    enable_database: bool = True
    database_url: str = "sqlite+aiosqlite:///./data/saas_assassin.db"
    database_pool_size: int = 5
    database_max_overflow: int = 10
    database_echo: bool = False
    auto_create_schema: bool = True

    queue_backend: QueueBackend = "memory"
    redis_url: str = "redis://localhost:6379/0"
    redis_queue_name: str = "assassin:jobs"
    worker_poll_timeout_seconds: int = 5

    storage_backend: StorageBackend = "local"
    local_storage_path: Path = Path("data/objects")
    storage_signing_secret: SecretStr = SecretStr("local-development-only")
    s3_endpoint_url: str | None = None
    s3_region: str = "us-east-1"
    s3_access_key: SecretStr = SecretStr("")
    s3_secret_key: SecretStr = SecretStr("")
    s3_bucket_quarantine: str = "assassin-quarantine"
    s3_bucket_files: str = "assassin-files"
    storage_presign_expires_seconds: int = 900
    max_upload_bytes: int = 25 * 1024 * 1024

    payment_provider: PaymentProviderBackend = "fake"
    payment_webhook_secret: SecretStr = SecretStr("local-payment-webhook-secret")
    payment_webhook_tolerance_seconds: int = 300
    billing_provider: BillingProviderBackend = "fake"
    billing_webhook_secret: SecretStr = SecretStr("local-billing-webhook-secret")
    billing_webhook_tolerance_seconds: int = 300

    integration_secret_key: SecretStr = SecretStr("local-integration-secret")
    webhook_secret_key: SecretStr = SecretStr("local-webhook-secret")
    webhook_worker_poll_seconds: int = 5
    webhook_delivery_batch_size: int = 100
    webhook_delivery_max_attempts: int = 8

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def allowed_origin_list(self) -> list[str]:
        return [value.strip() for value in self.allowed_origins.split(",") if value.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_environment == "production"

    @model_validator(mode="after")
    def validate_environment_contract(self) -> "Settings":
        if self.is_production:
            if not self.database_url.startswith(("postgresql+asyncpg://", "postgresql://")):
                raise ValueError("Production DATABASE_URL must use PostgreSQL")
            if self.queue_backend != "redis":
                raise ValueError("Production QUEUE_BACKEND must be redis")
            if self.storage_backend != "s3":
                raise ValueError("Production STORAGE_BACKEND must be s3")
            if self.auto_create_schema:
                raise ValueError("Production AUTO_CREATE_SCHEMA must be false; use Alembic")
            if self.payment_provider == "fake":
                raise ValueError("Production PAYMENT_PROVIDER cannot use fake")
            if self.billing_provider == "fake":
                raise ValueError("Production BILLING_PROVIDER cannot use fake")
            if (
                self.billing_webhook_secret.get_secret_value()
                == "local-billing-webhook-secret"
            ):
                raise ValueError(
                    "Production BILLING_WEBHOOK_SECRET must be replaced"
                )
            if self.integration_secret_key.get_secret_value() == "local-integration-secret":
                raise ValueError("Production INTEGRATION_SECRET_KEY must be replaced")
            if self.webhook_secret_key.get_secret_value() == "local-webhook-secret":
                raise ValueError("Production WEBHOOK_SECRET_KEY must be replaced")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
