import pytest

from app.infrastructure.secrets import LocalSecretCipher, SecretDecryptionError


def test_local_secret_cipher_encrypts_with_bound_context() -> None:
    cipher = LocalSecretCipher("unit-test-integration-secret")
    context = {
        "organization_id": "org-1",
        "connection_id": "connection-1",
    }

    encrypted = cipher.encrypt(b'{"api_token":"sandbox-token-1234"}', context)

    assert "sandbox-token-1234" not in encrypted.ciphertext
    assert cipher.decrypt(encrypted, context) == b'{"api_token":"sandbox-token-1234"}'
    with pytest.raises(SecretDecryptionError):
        cipher.decrypt(
            encrypted,
            {
                "organization_id": "org-2",
                "connection_id": "connection-1",
            },
        )
