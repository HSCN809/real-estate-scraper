# -*- coding: utf-8 -*-
"""
FastAPI dependencies for authentication
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional

from database.connection import get_db
from database.models import User
from .security import decode_token

# HTTP Bearer token scheme
security = HTTPBearer()
optional_security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency to get the current authenticated user.
    Raises HTTPException if token is invalid or user not found.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Geçersiz kimlik bilgileri",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = credentials.credentials
    payload = decode_token(token)

    if payload is None:
        raise credentials_exception

    # Check token type
    if payload.get("type") != "access":
        raise credentials_exception

    user_id: int = payload.get("sub")
    if user_id is None:
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
    """Dependency to ensure user is an admin"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Yönetici yetkisi gerekli"
        )
    return current_user


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_security),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """Optional authentication - returns None if no token provided"""
    if credentials is None:
        return None

    payload = decode_token(credentials.credentials)
    if payload is None or payload.get("type") != "access":
        return None

    user_id = payload.get("sub")
    if user_id is None:
        return None

    return db.query(User).filter(User.id == user_id, User.is_active == True).first()
