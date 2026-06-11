from dataclasses import dataclass

from .base import ObjectStorage


@dataclass(frozen=True)
class ScanResult:
    clean: bool
    reason: str | None = None


class FileScanner:
    malware_markers = (b"EICAR-STANDARD-ANTIVIRUS-TEST-FILE",)
    signatures: dict[str, tuple[bytes, ...]] = {
        "application/pdf": (b"%PDF-",),
        "image/png": (b"\x89PNG\r\n\x1a\n",),
        "image/jpeg": (b"\xff\xd8\xff",),
        "application/zip": (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08"),
    }
    allowed_content_types = {
        "application/pdf",
        "image/png",
        "image/jpeg",
        "application/zip",
        "text/csv",
        "text/plain",
    }

    def __init__(self, max_upload_bytes: int) -> None:
        self.max_upload_bytes = max_upload_bytes

    def scan(self, storage: ObjectStorage, key: str, content_type: str) -> ScanResult:
        if content_type not in self.allowed_content_types:
            return ScanResult(False, "unsupported_content_type")
        info = storage.stat(key)
        if info.size <= 0:
            return ScanResult(False, "empty_file")
        if info.size > self.max_upload_bytes:
            return ScanResult(False, "file_too_large")
        scan_prefix = storage.read_prefix(key, min(info.size, 1024 * 1024))
        if any(marker in scan_prefix for marker in self.malware_markers):
            return ScanResult(False, "malware_detected")
        expected = self.signatures.get(content_type)
        if expected is not None:
            if not any(scan_prefix.startswith(signature) for signature in expected):
                return ScanResult(False, "file_signature_mismatch")
        return ScanResult(True)
