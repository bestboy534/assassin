from typing import Any

from .base import ObjectInfo


class S3ObjectStorage:
    def __init__(
        self,
        *,
        endpoint_url: str | None,
        region: str,
        access_key: str,
        secret_key: str,
        quarantine_bucket: str,
        files_bucket: str,
    ) -> None:
        import boto3

        self.client: Any = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            region_name=region,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
        )
        self.quarantine_bucket = quarantine_bucket
        self.files_bucket = files_bucket

    def presign_upload(self, key: str, content_type: str, expires: int) -> str:
        bucket, object_key = self._location(key)
        return str(
            self.client.generate_presigned_url(
                "put_object",
                Params={"Bucket": bucket, "Key": object_key, "ContentType": content_type},
                ExpiresIn=expires,
            )
        )

    def presign_download(self, key: str, expires: int) -> str:
        bucket, object_key = self._location(key)
        return str(
            self.client.generate_presigned_url(
                "get_object",
                Params={"Bucket": bucket, "Key": object_key},
                ExpiresIn=expires,
            )
        )

    def move(self, source: str, destination: str) -> None:
        source_bucket, source_key = self._location(source)
        destination_bucket, destination_key = self._location(destination)
        self.client.copy_object(
            Bucket=destination_bucket,
            Key=destination_key,
            CopySource={"Bucket": source_bucket, "Key": source_key},
        )
        self.client.delete_object(Bucket=source_bucket, Key=source_key)

    def delete(self, key: str) -> None:
        bucket, object_key = self._location(key)
        self.client.delete_object(Bucket=bucket, Key=object_key)

    def stat(self, key: str) -> ObjectInfo:
        bucket, object_key = self._location(key)
        response = self.client.head_object(Bucket=bucket, Key=object_key)
        return ObjectInfo(
            size=int(response["ContentLength"]),
            content_type=response.get("ContentType"),
        )

    def read_prefix(self, key: str, limit: int) -> bytes:
        bucket, object_key = self._location(key)
        response = self.client.get_object(
            Bucket=bucket,
            Key=object_key,
            Range=f"bytes=0-{max(limit - 1, 0)}",
        )
        return bytes(response["Body"].read())

    def write_bytes(self, key: str, data: bytes, content_type: str) -> None:
        bucket, object_key = self._location(key)
        self.client.put_object(
            Bucket=bucket,
            Key=object_key,
            Body=data,
            ContentType=content_type,
        )

    def read_bytes(self, key: str) -> bytes:
        bucket, object_key = self._location(key)
        response = self.client.get_object(Bucket=bucket, Key=object_key)
        return bytes(response["Body"].read())

    def ping(self) -> bool:
        try:
            self.client.head_bucket(Bucket=self.quarantine_bucket)
            self.client.head_bucket(Bucket=self.files_bucket)
        except Exception:
            return False
        return True

    def _location(self, key: str) -> tuple[str, str]:
        prefix, _, object_key = key.partition("/")
        if prefix == "quarantine":
            return self.quarantine_bucket, object_key
        if prefix == "files":
            return self.files_bucket, object_key
        raise ValueError(f"Unknown storage key prefix: {prefix}")
