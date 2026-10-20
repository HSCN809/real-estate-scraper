"""Şifre hashleme ve JWT token yönetimi"""

import hashlib
import os
from datetime import datetime, timedelta
from typing import Any

import jwt
from jwt import InvalidTokenError
from passlib.context import CryptContext

# Şifre hashleme konfigürasyonu
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

_INSECURE_SECRETS = {
    "",
    "your-secret-key-change-in-production",
    "your-secret-key-change-in-production-abc123xyz789",
    "replace-with-at-least-32-random-characters",
    "CHANGE_THIS_TO_A_RANDOM_SECRET_KEY",
}
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_DAYS = int(os.getenv("ACCESS_TOKEN_EXPIRE_DAYS", "7"))


def _jwt_secret() -> str:
    key = os.getenv("JWT_SECRET_KEY", "").strip()
    if key in _INSECURE_SECRETS or len(key) < 32:
        raise RuntimeError(
            "JWT_SECRET_KEY must be a non-placeholder value of at least 32 characters"
        )
    return key


def password_stamp(hashed_password: str) -> str:
    return hashlib.sha256(hashed_password.encode()).hexdigest()[:16]


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Şifreyi hash'iyle doğrula"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """bcrypt ile şifre hash'i oluştur"""
    return pwd_context.hash(password)


def create_access_token(
    data: dict[str, Any], expires_delta: timedelta | None = None
) -> str:
    """JWT erişim token'ı oluştur"""
    to_encode = data.copy()
    # JWT spesifikasyonu 'sub' alanının string olmasını gerektirir
    if "sub" in to_encode:
        to_encode["sub"] = str(to_encode["sub"])
    expire = datetime.utcnow() + (
        expires_delta or timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    )
    to_encode.update({"exp": expire, "type": "access"})
    token = jwt.encode(to_encode, _jwt_secret(), algorithm=ALGORITHM)
    return token


def decode_token(token: str) -> dict[str, Any] | None:
    """JWT token'ı çöz ve doğrula"""
    try:
        payload = jwt.decode(token, _jwt_secret(), algorithms=[ALGORITHM])
        return payload
    except InvalidTokenError:
        return None
