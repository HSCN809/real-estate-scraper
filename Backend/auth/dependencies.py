"""Kimlik doğrulama bağımlılıkları"""

from collections import OrderedDict
from dataclasses import dataclass
from threading import Lock
from time import monotonic
from typing import Any
from weakref import WeakKeyDictionary

from database.connection import get_db
from database.models import User
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from .security import decode_token, password_stamp

COOKIE_NAME = "session_token"
_USER_CACHE_TTL_SECONDS = 15.0
_USER_CACHE_MAX_ENTRIES = 256
_user_cache: OrderedDict[tuple[int, int], tuple[float, "CachedUser"]] = OrderedDict()
_bind_ids: WeakKeyDictionary[Any, int] = WeakKeyDictionary()
_cache_lock = Lock()
_next_bind_seq = 0


@dataclass(frozen=True)
class CachedUser:
    """Read-only snapshot cached across authenticated requests."""

    id: int
    username: str
    email: str
    hashed_password: str
    is_active: bool
    is_admin: bool


def invalidate_user_cache(user_id: int | None = None) -> None:
    """Drop cached user snapshots on account/password mutation."""
    with _cache_lock:
        if user_id is None:
            _user_cache.clear()
            return
        for key in [k for k in _user_cache if k[1] == user_id]:
            del _user_cache[key]


def _bind_token(db: Session) -> int:
    global _next_bind_seq
    bind = db.get_bind()
    bind = getattr(bind, "engine", bind)
    token = _bind_ids.get(bind)
    if token is None:
        _next_bind_seq += 1
        token = _next_bind_seq
        _bind_ids[bind] = token
    return token


def _resolve_user(request: Request, db: Session, *, required: bool) -> Any:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Geçersiz kimlik bilgileri",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = request.cookies.get(COOKIE_NAME)
    if not token:
        if required:
            raise credentials_exception
        return None

    payload = decode_token(token)
    if payload is None or payload.get("type") != "access":
        if required:
            raise credentials_exception
        return None

    user_id_raw = payload.get("sub")
    try:
        user_id = int(user_id_raw) if user_id_raw is not None else None
    except (TypeError, ValueError):
        user_id = None
    if user_id is None:
        if required:
            raise credentials_exception
        return None

    token_pwd = payload.get("pwd")
    with _cache_lock:
        cache_key = (_bind_token(db), user_id)
        cached_entry = _user_cache.get(cache_key)
        now = monotonic()
        if cached_entry is not None:
            expires_at, cached_user = cached_entry
            if now < expires_at and token_pwd == password_stamp(cached_user.hashed_password):
                _user_cache.move_to_end(cache_key)
                if not cached_user.is_active:
                    if required:
                        raise HTTPException(
                            status_code=status.HTTP_403_FORBIDDEN,
                            detail="Hesap devre dışı",
                        )
                    return None
                return cached_user
            del _user_cache[cache_key]

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        if required:
            raise credentials_exception
        return None

    snapshot = CachedUser(
        id=user.id,
        username=user.username,
        email=user.email,
        hashed_password=user.hashed_password,
        is_active=bool(user.is_active),
        is_admin=bool(user.is_admin),
    )
    with _cache_lock:
        _user_cache[cache_key] = (monotonic() + _USER_CACHE_TTL_SECONDS, snapshot)
        _user_cache.move_to_end(cache_key)
        while len(_user_cache) > _USER_CACHE_MAX_ENTRIES:
            _user_cache.popitem(last=False)

    if not user.is_active:
        if required:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Hesap devre dışı"
            )
        return None

    if token_pwd != password_stamp(user.hashed_password):
        if required:
            raise credentials_exception
        return None

    return snapshot


def get_current_user(request: Request, db: Session = Depends(get_db)) -> Any:
    """HTTP-only cookie'den mevcut kullanıcıyı al"""
    return _resolve_user(request, db, required=True)


async def get_current_active_admin(
    current_user: Any = Depends(get_current_user),
) -> Any:
    """Kullanıcının yönetici olduğunu doğrula"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Yönetici yetkisi gerekli"
        )
    return current_user


async def get_optional_user(
    request: Request, db: Session = Depends(get_db)
) -> Any | None:
    """Opsiyonel kimlik doğrulama - geçerli cookie yoksa None döner"""
    return _resolve_user(request, db, required=False)
