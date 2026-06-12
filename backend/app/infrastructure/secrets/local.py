import base64
import hashlib
import json
from dataclasses import dataclass
from typing import Protocol

from cryptography.fernet import Fernet, InvalidToken


@dataclass(frozen=True)
class EncryptedSecret:
    cipher_suite: str
    ciphertext: str


class SecretDecryptionError(Exception):
    pass


class SecretCipher(Protocol):
    def encrypt(self, plaintext: bytes, context: dict[str, str]) -> EncryptedSecret: ...

    def decrypt(self, secret: EncryptedSecret, context: dict[str, str]) -> bytes: ...


class LocalSecretCipher:
    cipher_suite = "local-fernet-v1"

    def __init__(self, master_key: str) -> None:
        if not master_key:
            raise ValueError("Secret master key is required")
        self.master_key = master_key.encode("utf-8")

    def encrypt(self, plaintext: bytes, context: dict[str, str]) -> EncryptedSecret:
        return EncryptedSecret(
            cipher_suite=self.cipher_suite,
            ciphertext=self._fernet(context).encrypt(plaintext).decode("utf-8"),
        )

    def decrypt(self, secret: EncryptedSecret, context: dict[str, str]) -> bytes:
        if secret.cipher_suite != self.cipher_suite:
            raise SecretDecryptionError("Unsupported secret cipher suite")
        try:
            return self._fernet(context).decrypt(secret.ciphertext.encode("utf-8"))
        except InvalidToken as exc:
            raise SecretDecryptionError("Secret context does not match") from exc

    def _fernet(self, context: dict[str, str]) -> Fernet:
        canonical_context = json.dumps(context, sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256(
            self.master_key + b":" + canonical_context.encode("utf-8")
        ).digest()
        return Fernet(base64.urlsafe_b64encode(digest))
