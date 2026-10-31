"""Encryption of secrets at rest (exchange API credentials).

Fernet = AES-128-CBC + HMAC-SHA256, authenticated: a tampered or wrong-key token fails to open.
Several keys may be configured (first encrypts, all decrypt) so the master key can be rotated
without losing access to existing records.
"""

import hashlib
from collections.abc import Sequence

from cryptography.fernet import Fernet, InvalidToken, MultiFernet

from core.errors import LostCryptoError


class VaultNotConfigured(LostCryptoError):
    """CREDENTIAL_MASTER_KEYS is missing or invalid."""


class VaultError(LostCryptoError):
    """A stored secret could not be opened (wrong key or corrupted data)."""


class CredentialVault:
    def __init__(self, keys: Sequence[str]) -> None:
        if not keys:
            raise VaultNotConfigured("CREDENTIAL_MASTER_KEYS is not set")
        try:
            self._fernet = MultiFernet([Fernet(k.encode()) for k in keys])
        except ValueError as exc:
            raise VaultNotConfigured(
                "CREDENTIAL_MASTER_KEYS contains an invalid Fernet key"
            ) from exc
        # Identifies which key sealed a record; reveals nothing usable about the key.
        self.key_id = hashlib.sha256(keys[0].encode()).hexdigest()[:8]

    def seal(self, plaintext: str) -> bytes:
        return self._fernet.encrypt(plaintext.encode())

    def open(self, token: bytes) -> str:
        try:
            return self._fernet.decrypt(token).decode()
        except InvalidToken as exc:
            raise VaultError(
                "stored credentials cannot be decrypted with the configured keys"
            ) from exc

    def rotate(self, token: bytes) -> bytes:
        """Re-encrypt with the current (first) key."""
        return self._fernet.rotate(token)
