# -*- coding: utf-8 -*-
"""Kimlik doğrulama bağımlılıkları"""

from fastapi import Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import Optional

from database.connection import get_db
from database.models import User
from .security import decode_token

COOKIE_NAME = "session_token"


async def get_current_user(
    request: Request,
    db: Session = Depends(get_db)
) -> User:
    """HTTP-only cookie'den mevcut kullanıcıyı al"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Geçersiz kimlik bilgileri",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Cookie'den token al
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise credentials_exception

    payload = decode_token(token)

    if payload is None:
        raise credentials_exception

    # Token tipini kontrol et
    if payload.get("type") != "access":
        raise credentials_exception

    user_id_raw = payload.get("sub")
    if user_id_raw is None:
        raise credentials_exception

    try:
        user_id = int(user_id_raw)
    except (TypeError, ValueError):
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Hesap devre dışı"
        )

    return user


async def get_current_active_admin(
    current_user: User = Depends(get_current_user)
) -> User:
    """Kullanıcının yönetici olduğunu doğrula"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Yönetici yetkisi gerekli"
        )
    return current_user


async def get_optional_user(
    request: Request,
    db: Session = Depends(get_db)
) -> Optional[User]:
    """Opsiyonel kimlik doğrulama - geçerli cookie yoksa None döner"""
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None

    payload = decode_token(token)
    if payload is None or payload.get("type") != "access":
        return None

    user_id_raw = payload.get("sub")
    if user_id_raw is None:
        return None

    try:
        user_id = int(user_id_raw)
    except (TypeError, ValueError):
        return None

    return db.query(User).filter(User.id == user_id, User.is_active == True).first()
