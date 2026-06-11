import hashlib
import hmac
import shutil
import time
from pathlib import Path
from urllib.parse import quote

from .base import ObjectInfo


class InvalidStorageSignature(ValueError):
    pass


class LocalObjectStorage:
    def __init__(self, root: Path, signing_secret: str) -> None:
        self.root = root.resolve()
        self.signing_secret = signing_secret.encode("utf-8")
        self.root.mkdir(parents=True, exist_ok=True)

    def presign_upload(self, key: str, content_type: str, expires: int) -> str:
        del content_type
        return self._signed_url("/api/v1/files/local-upload", key, expires)

    def presign_download(self, key: str, expires: int) -> str:
        return self._signed_url("/api/v1/files/local-download", key, expires)

    def move(self, source: str, destination: str) -> None:
        source_path = self._path(source)
        destination_path = self._path(destination)
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source_path), str(destination_path))

    def delete(self, key: str) -> None:
        self._path(key).unlink(missing_ok=True)

    def stat(self, key: str) -> ObjectInfo:
        path = self._path(key)
        return ObjectInfo(size=path.stat().st_size)

    def read_prefix(self, key: str, limit: int) -> bytes:
        with self._path(key).open("rb") as handle:
            return handle.read(limit)

    def write_bytes(self, key: str, data: bytes, content_type: str) -> None:
        del content_type
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def read_bytes(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    def ping(self) -> bool:
        try:
            self.root.mkdir(parents=True, exist_ok=True)
            return self.root.is_dir()
        except OSError:
            return False

    def verify(self, operation: str, key: str, expires: int, signature: str) -> None:
        if expires < int(time.time()):
            raise InvalidStorageSignature("Storage URL has expired")
        expected = self._signature(operation, key, expires)
        if not hmac.compare_digest(signature, expected):
            raise InvalidStorageSignature("Invalid storage URL signature")

    def _signed_url(self, operation: str, key: str, ttl: int) -> str:
        expires = int(time.time()) + ttl
        signature = self._signature(operation, key, expires)
        return f"{operation}/{quote(key, safe='/')}?expires={expires}&signature={signature}"

    def _signature(self, operation: str, key: str, expires: int) -> str:
        message = f"{operation}\n{key}\n{expires}".encode()
        return hmac.new(self.signing_secret, message, hashlib.sha256).hexdigest()

    def _path(self, key: str) -> Path:
        candidate = (self.root / key).resolve()
        if candidate != self.root and self.root not in candidate.parents:
            raise ValueError("Object key escapes storage root")
        return candidate
