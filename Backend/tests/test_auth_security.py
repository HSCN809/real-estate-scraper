"""JWT secret and password-stamp checks."""

import os

import pytest

os.environ.setdefault(
    "JWT_SECRET_KEY", "test-secret-key-at-least-32-characters-long"
)

from auth.security import (  # noqa: E402
    create_access_token,
    decode_token,
    password_stamp,
)


def test_rejects_placeholder_secret(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
    with pytest.raises(RuntimeError):
        create_access_token({"sub": "1"})


def test_password_stamp_changes_with_hash():
    old_hash = "bcrypt-old"
    new_hash = "bcrypt-new"
    token = create_access_token({"sub": "1", "pwd": password_stamp(old_hash)})
    payload = decode_token(token)
    assert payload is not None
    assert payload["pwd"] == password_stamp(old_hash)
    assert payload["pwd"] != password_stamp(new_hash)


def test_default_expiry_is_seven_days(monkeypatch):
    monkeypatch.delenv("ACCESS_TOKEN_EXPIRE_DAYS", raising=False)
    import importlib

    import auth.security as security

    reloaded = importlib.reload(security)
    assert reloaded.ACCESS_TOKEN_EXPIRE_DAYS == 7
