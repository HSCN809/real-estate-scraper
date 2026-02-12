# -*- coding: utf-8 -*-
"""Şifre hashleme ve JWT token yönetimi"""

import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from passlib.context import CryptContext
from jose import JWTError, jwt

# Şifre hashleme konfigürasyonu
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Ortam değişkenlerinden JWT konfigürasyonu
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production-abc123xyz789")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_DAYS = int(os.getenv("ACCESS_TOKEN_EXPIRE_DAYS", "30"))


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Şifreyi hash'iyle doğrula"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """bcrypt ile şifre hash'i oluştur"""
    return pwd_context.hash(password)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """JWT erişim token'ı oluştur"""
    to_encode = data.copy()
    # JWT spesifikasyonu 'sub' alanının string olmasını gerektirir
    if "sub" in to_encode:
        to_encode["sub"] = str(to_encode["sub"])
    expire = datetime.utcnow() + (expires_delta or timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS))
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """JWT token'ı çöz ve doğrula"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None
