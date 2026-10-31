from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest

from core.config import AppEnv, Settings
from core.security.auth import InsecureConfiguration, assert_secure_configuration
from core.security.passwords import (
    MIN_PASSWORD_LENGTH,
    PasswordService,
    WeakPassword,
    validate_password,
)
from core.security.tokens import ISSUER, InvalidToken, TokenCodec

SECRET = "s" * 40
NOW = datetime(2025, 1, 1, 12, tzinfo=UTC)


# --- passwords --------------------------------------------------------------------------------


def test_hashes_are_argon2id_salted_and_verifiable() -> None:
    service = PasswordService()
    first, second = service.hash("correct horse battery"), service.hash("correct horse battery")
    assert first.startswith("$argon2id$") and first != second  # random salt
    assert service.verify(first, "correct horse battery")
    assert not service.verify(first, "correct horse batterY")
    assert not service.verify("not-a-hash", "whatever")  # garbage is a mismatch, not a crash
    assert not service.needs_rehash(first)
    service.verify_dummy("anything")  # exists so unknown users cost the same time


@pytest.mark.parametrize(
    ("password", "username"),
    [
        ("short1", ""),
        ("x" * 300, ""),
        ("aaaaaaaaaaaaaaaa", ""),  # one repeated character
        ("password1234", ""),  # on the common list
        ("my-daniel-secret-1", "daniel"),  # contains the username
    ],
)
def test_weak_passwords_are_refused(password: str, username: str) -> None:
    with pytest.raises(WeakPassword):
        validate_password(password, username)


def test_a_long_passphrase_is_accepted_without_composition_rules() -> None:
    validate_password("correct horse battery staple", "daniel")
    assert MIN_PASSWORD_LENGTH == 12


# --- access tokens ----------------------------------------------------------------------------


def test_access_token_round_trip() -> None:
    codec = TokenCodec(SECRET, timedelta(minutes=15))
    user_id = uuid4()
    claims = codec.decode(codec.issue(user_id, "daniel", "admin", NOW), NOW)
    assert (claims.user_id, claims.username, claims.role) == (user_id, "daniel", "admin")
    assert claims.expires_at == NOW + timedelta(minutes=15)
    assert codec.lifetime_seconds == 900


def test_expired_tampered_and_foreign_tokens_are_rejected() -> None:
    codec = TokenCodec(SECRET, timedelta(minutes=15))
    token = codec.issue(uuid4(), "daniel", "admin", NOW)

    with pytest.raises(InvalidToken):
        codec.decode(token, NOW + timedelta(minutes=16))  # expired
    with pytest.raises(InvalidToken):
        codec.decode(token[:-3] + "abc", NOW)  # tampered signature
    with pytest.raises(InvalidToken):
        TokenCodec("o" * 40, timedelta(minutes=15)).decode(token, NOW)  # signed by someone else
    with pytest.raises(InvalidToken):
        codec.decode("not.a.jwt")


def test_alg_none_and_wrong_kind_tokens_cannot_be_used() -> None:
    codec = TokenCodec(SECRET, timedelta(minutes=15))
    claims = {
        "iss": ISSUER,
        "sub": str(uuid4()),
        "usr": "x",
        "role": "admin",
        "typ": "access",
        "iat": int(NOW.timestamp()),
        "exp": int((NOW + timedelta(hours=1)).timestamp()),
    }
    unsigned = jwt.encode(claims, key="", algorithm="none")
    with pytest.raises(InvalidToken):
        codec.decode(unsigned, NOW)  # the classic "alg: none" forgery
    refresh_kind = jwt.encode({**claims, "typ": "refresh"}, SECRET, algorithm="HS256")
    with pytest.raises(InvalidToken, match="not an access token"):
        codec.decode(refresh_kind, NOW)
    wrong_issuer = jwt.encode({**claims, "iss": "someone-else"}, SECRET, algorithm="HS256")
    with pytest.raises(InvalidToken):
        codec.decode(wrong_issuer, NOW)


def test_the_signing_secret_must_be_long_enough() -> None:
    with pytest.raises(ValueError, match="at least 32"):
        TokenCodec("short", timedelta(minutes=15))


# --- configuration ----------------------------------------------------------------------------


def test_auth_settings_and_their_safe_defaults() -> None:
    local = Settings(_env_file=None)  # type: ignore[call-arg]
    assert not local.auth_enabled and not local.secure_cookies  # developer machine
    users = Settings(_env_file=None, jwt_secret=SECRET)  # type: ignore[call-arg]
    assert users.auth_enabled
    prod = Settings(_env_file=None, app_env=AppEnv.PROD, jwt_secret=SECRET)  # type: ignore[call-arg]
    assert prod.secure_cookies  # cookies are Secure everywhere except local
    assert Settings(_env_file=None, jwt_secret="").auth_enabled is False  # type: ignore[call-arg]
    assert SECRET not in repr(users)  # SecretStr


def test_production_needs_some_form_of_authentication() -> None:
    with pytest.raises(InsecureConfiguration):
        assert_secure_configuration(Settings(_env_file=None, app_env=AppEnv.PROD))  # type: ignore[call-arg]
    assert_secure_configuration(
        Settings(_env_file=None, app_env=AppEnv.PROD, jwt_secret=SECRET)  # type: ignore[call-arg]
    )
    assert_secure_configuration(
        Settings(_env_file=None, app_env=AppEnv.PROD, api_token="t")  # type: ignore[call-arg]
    )
