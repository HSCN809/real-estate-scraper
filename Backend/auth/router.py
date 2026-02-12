# -*- coding: utf-8 -*-
"""
Authentication API endpoints
"""

import os
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from sqlalchemy.orm import Session
from sqlalchemy import or_
from datetime import datetime

from database.connection import get_db
from database.models import User
from .security import verify_password, get_password_hash, create_access_token, ACCESS_TOKEN_EXPIRE_DAYS
from .dependencies import get_current_user
from .schemas import (
    UserCreate, UserLogin, UserResponse,
    ChangePasswordRequest, UpdateProfileRequest
)

router = APIRouter(prefix="/auth", tags=["Authentication"])

COOKIE_NAME = "session_token"
COOKIE_MAX_AGE = ACCESS_TOKEN_EXPIRE_DAYS * 24 * 60 * 60  # seconds
IS_PRODUCTION = os.getenv("ENVIRONMENT", "development") == "production"


def _set_auth_cookie(response: Response, token: str):
    """Set HTTP-only auth cookie on response.
    Production: secure=True + samesite=none (HTTPS required)
    Development: secure=False + samesite=lax (HTTP localhost)
    """
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        secure=IS_PRODUCTION,
        samesite="none" if IS_PRODUCTION else "lax",
        max_age=COOKIE_MAX_AGE,
        path="/",
    )


def _clear_auth_cookie(response: Response):
    """Clear auth cookie from response"""
    response.delete_cookie(
        key=COOKIE_NAME,
        path="/",
        secure=IS_PRODUCTION,
        samesite="none" if IS_PRODUCTION else "lax",
    )


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, response: Response, db: Session = Depends(get_db)):
    """Register a new user"""
    # Check if username exists
    existing = db.query(User).filter(
        or_(User.username == user_data.username, User.email == user_data.email)
    ).first()

    if existing:
        if existing.username == user_data.username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Bu kullanıcı adı zaten kullanılıyor"
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bu e-posta adresi zaten kullanılıyor"
        )

    # Create user
    user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        is_active=True,
        is_admin=False
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Generate token and set cookie
    token_data = {"sub": user.id, "username": user.username}
    access_token = create_access_token(token_data)
    _set_auth_cookie(response, access_token)

    return UserResponse.model_validate(user)


@router.post("/login", response_model=UserResponse)
async def login(credentials: UserLogin, response: Response, db: Session = Depends(get_db)):
    """Authenticate user and return token via cookie"""
    # Find user by username or email
    user = db.query(User).filter(
        or_(User.username == credentials.username, User.email == credentials.username)
    ).first()

    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Geçersiz kullanıcı adı veya şifre"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Hesap devre dışı"
        )

    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()

    # Generate token and set cookie
    token_data = {"sub": user.id, "username": user.username}
    access_token = create_access_token(token_data)
    _set_auth_cookie(response, access_token)

    return UserResponse.model_validate(user)


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    return UserResponse.model_validate(current_user)


@router.put("/me", response_model=UserResponse)
async def update_profile(
    update_data: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user profile (username/email)"""
    if update_data.username and update_data.username != current_user.username:
        existing = db.query(User).filter(
            User.username == update_data.username,
            User.id != current_user.id
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Bu kullanıcı adı zaten kullanılıyor"
            )
        current_user.username = update_data.username

    if update_data.email and update_data.email != current_user.email:
        existing = db.query(User).filter(
            User.email == update_data.email,
            User.id != current_user.id
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Bu e-posta adresi zaten kullanılıyor"
            )
        current_user.email = update_data.email

    db.commit()
    db.refresh(current_user)

    return UserResponse.model_validate(current_user)


@router.post("/change-password")
async def change_password(
    password_data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Change user password"""
    if not verify_password(password_data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mevcut şifre yanlış"
        )

    current_user.hashed_password = get_password_hash(password_data.new_password)
    db.commit()

    return {"message": "Şifre başarıyla değiştirildi"}


@router.post("/logout")
async def logout(response: Response):
    """Logout user by clearing auth cookie"""
    _clear_auth_cookie(response)
    return {"message": "Oturum kapatıldı"}
