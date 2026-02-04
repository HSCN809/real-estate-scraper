# -*- coding: utf-8 -*-
"""
Authentication API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_
from datetime import datetime

from database.connection import get_db
from database.models import User
from .security import verify_password, get_password_hash, create_access_token
from .dependencies import get_current_user
from .schemas import (
    UserCreate, UserLogin, UserResponse, TokenResponse,
    ChangePasswordRequest, UpdateProfileRequest
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
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

    # Generate token
    token_data = {"sub": user.id, "username": user.username}
    access_token = create_access_token(token_data)

    return TokenResponse(
        access_token=access_token,
        user=UserResponse.model_validate(user)
    )


@router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """Authenticate user and return token"""
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

    # Generate token
    token_data = {"sub": user.id, "username": user.username}
    access_token = create_access_token(token_data)

    return TokenResponse(
        access_token=access_token,
        user=UserResponse.model_validate(user)
    )


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
