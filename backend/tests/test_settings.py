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
    )
    assert settings.is_production
