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


def test_get_current_user_caches_and_invalidates_on_password_change():
    from auth.dependencies import get_current_user, invalidate_user_cache
    from auth.security import get_password_hash, password_stamp
    from database.models import Base, User
    from fastapi import HTTPException
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import Session
    from sqlalchemy.pool import StaticPool
    from starlette.requests import Request

    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    sql_count = [0]

    @event.listens_for(engine, "before_cursor_execute")
    def _count(*_args):
        sql_count[0] += 1

    old_hash = get_password_hash("OldPass123")
    new_hash = get_password_hash("NewPass123")
    with Session(engine) as db:
        user = User(
            username="cacheuser",
            email="cache@example.com",
            hashed_password=old_hash,
            is_active=True,
            is_admin=False,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        old_token = create_access_token(
            {"sub": user.id, "username": user.username, "pwd": password_stamp(old_hash)}
        )
        req = Request(
            {"type": "http", "headers": [(b"cookie", f"session_token={old_token}".encode("latin1"))]}
        )

        sql_count[0] = 0
        assert get_current_user(req, db).username == "cacheuser"
        assert get_current_user(req, db).username == "cacheuser"
        assert sql_count[0] == 1

        user.hashed_password = new_hash
        db.commit()
        invalidate_user_cache(user.id)

        with pytest.raises(HTTPException) as exc:
            get_current_user(req, db)
        assert exc.value.status_code == 401

    engine.dispose()


def test_password_hash_argon2_and_legacy_bcrypt_verification():
    from pwdlib.hashers.bcrypt import BcryptHasher

    from auth.security import get_password_hash, verify_password

    argon_hash = get_password_hash("StrongPass123!")
    assert argon_hash.startswith("$argon2id$")
    assert verify_password("StrongPass123!", argon_hash) is True
    assert verify_password("WrongPass", argon_hash) is False

    legacy_hash = BcryptHasher().hash("LegacyPass123!")
    assert legacy_hash.startswith("$2b$")
    assert verify_password("LegacyPass123!", legacy_hash) is True
    assert verify_password("WrongPass", legacy_hash) is False
