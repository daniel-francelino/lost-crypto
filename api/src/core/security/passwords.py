"""Password hashing (argon2id) and the password policy."""

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from core.errors import DomainError

MIN_PASSWORD_LENGTH = 12
_COMMON = frozenset(
    {
        "password1234",
        "123456789012",
        "qwertyuiop12",
        "administrator",
        "letmein12345",
        "changeme1234",
    }
)


class WeakPassword(DomainError):
    pass


def validate_password(password: str, username: str = "") -> None:
    """Length matters more than composition rules; refuse the obviously guessable."""
    if len(password) < MIN_PASSWORD_LENGTH:
        raise WeakPassword(f"password must have at least {MIN_PASSWORD_LENGTH} characters")
    if len(password) > 256:
        raise WeakPassword("password is too long (max 256 characters)")
    lowered = password.lower()
    if username and username.lower() in lowered:
        raise WeakPassword("password must not contain the username")
    if len(set(password)) < 5 or lowered in _COMMON:
        raise WeakPassword("password is too easy to guess")


class PasswordService:
    """argon2id with the library's current recommended parameters. CPU-bound: callers run it
    in a worker thread so the event loop keeps serving requests."""

    def __init__(self) -> None:
        self._hasher = PasswordHasher()
        # Verified against when a username does not exist, so "unknown user" and "wrong
        # password" take the same time and cannot be told apart.
        self._dummy = self._hasher.hash("not-a-real-password-for-timing")

    def hash(self, password: str) -> str:
        return self._hasher.hash(password)

    def verify(self, password_hash: str, password: str) -> bool:
        try:
            return self._hasher.verify(password_hash, password)
        except (VerifyMismatchError, VerificationError, InvalidHashError):
            return False

    def verify_dummy(self, password: str) -> None:
        self.verify(self._dummy, password)

    def needs_rehash(self, password_hash: str) -> bool:
        return self._hasher.check_needs_rehash(password_hash)
