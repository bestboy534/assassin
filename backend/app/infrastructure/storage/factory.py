from app.core.config import Settings, get_settings

from .base import ObjectStorage
from .local import LocalObjectStorage
from .s3 import S3ObjectStorage


def build_storage(settings: Settings | None = None) -> ObjectStorage:
    resolved = settings or get_settings()
    if resolved.storage_backend == "s3":
        return S3ObjectStorage(
            endpoint_url=resolved.s3_endpoint_url,
            region=resolved.s3_region,
            access_key=resolved.s3_access_key.get_secret_value(),
            secret_key=resolved.s3_secret_key.get_secret_value(),
            quarantine_bucket=resolved.s3_bucket_quarantine,
            files_bucket=resolved.s3_bucket_files,
        )
    return LocalObjectStorage(
        resolved.local_storage_path,
        resolved.storage_signing_secret.get_secret_value(),
    )
