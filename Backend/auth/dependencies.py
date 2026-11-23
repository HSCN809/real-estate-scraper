"""Kimlik doğrulama bağımlılıkları"""


from database.connection import get_db
from database.models import User
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from .security import decode_token, password_stamp

COOKIE_NAME = "session_token"


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
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
            status_code=status.HTTP_403_FORBIDDEN, detail="Hesap devre dışı"
        )

    if payload.get("pwd") != password_stamp(user.hashed_password):
        raise credentials_exception

    return user


async def get_current_active_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """Kullanıcının yönetici olduğunu doğrula"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Yönetici yetkisi gerekli"
        )
    return current_user


async def get_optional_user(
    request: Request, db: Session = Depends(get_db)
) -> User | None:
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

    user = db.query(User).filter(User.id == user_id, User.is_active).first()
    if user is None or payload.get("pwd") != password_stamp(user.hashed_password):
        return None
    return user
