import pytest
from pydantic import ValidationError

from app.config import Settings


def test_production_requires_managed_backends() -> None:
    with pytest.raises(ValidationError):
        Settings(app_environment="production")


def test_production_accepts_postgres_redis_and_s3() -> None:
    settings = Settings(
        app_environment="production",
        database_url="postgresql+asyncpg://user:password@db/app",
        auto_create_schema=False,
        queue_backend="redis",
        storage_backend="s3",
        payment_provider="stripe_issuing",
        integration_secret_key="production-integration-secret",
        webhook_secret_key="production-webhook-secret",
    )
    assert settings.is_production
    assert settings.payment_provider == "stripe_issuing"


def test_production_rejects_default_integration_secret() -> None:
    with pytest.raises(ValidationError, match="INTEGRATION_SECRET_KEY"):
        Settings(
            app_environment="production",
            database_url="postgresql+asyncpg://user:password@db/app",
            auto_create_schema=False,
            queue_backend="redis",
            storage_backend="s3",
            payment_provider="stripe_issuing",
        )


def test_production_rejects_default_webhook_secret() -> None:
    with pytest.raises(ValueError, match="WEBHOOK_SECRET_KEY"):
        Settings(
            app_environment="production",
            database_url="postgresql+asyncpg://user:pass@db/app",
            queue_backend="redis",
            storage_backend="s3",
            auto_create_schema=False,
            payment_provider="stripe_issuing",
            integration_secret_key="production-integration-secret",
        )


def test_production_rejects_fake_payment_provider() -> None:
    with pytest.raises(ValidationError, match="PAYMENT_PROVIDER"):
        Settings(
            app_environment="production",
            database_url="postgresql+asyncpg://user:password@db/app",
            auto_create_schema=False,
            queue_backend="redis",
            storage_backend="s3",
            payment_provider="fake",
        )
