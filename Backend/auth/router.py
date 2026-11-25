"""Kimlik doğrulama API endpoint'leri"""

import os
from datetime import datetime

from database.connection import get_db
from database.models import User
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from .dependencies import get_current_user, invalidate_user_cache
from .schemas import (
    ChangePasswordRequest,
    UpdateProfileRequest,
    UserCreate,
    UserLogin,
    UserResponse,
)
from .security import (
    ACCESS_TOKEN_EXPIRE_DAYS,
    create_access_token,
    get_password_hash,
    password_stamp,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])

COOKIE_NAME = "session_token"
COOKIE_MAX_AGE = ACCESS_TOKEN_EXPIRE_DAYS * 24 * 60 * 60  # seconds
IS_PRODUCTION = os.getenv("ENVIRONMENT", "development") == "production"


def _set_auth_cookie(response: Response, token: str):
    """HTTP-only auth cookie'yi ayarla"""
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
    """Auth cookie'yi temizle"""
    response.delete_cookie(
        key=COOKIE_NAME,
        path="/",
        secure=IS_PRODUCTION,
        samesite="none" if IS_PRODUCTION else "lax",
    )


@router.post(
    "/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
def register(user_data: UserCreate, response: Response, db: Session = Depends(get_db)):
    """Yeni kullanıcı kaydı"""
    # Kullanıcı adı var mı kontrol et
    existing = (
        db.query(User)
        .filter(or_(User.username == user_data.username, User.email == user_data.email))
        .first()
    )

    if existing:
        if existing.username == user_data.username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Bu kullanıcı adı zaten kullanılıyor",
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bu e-posta adresi zaten kullanılıyor",
        )

    # Kullanıcı oluştur
    user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        is_active=True,
        is_admin=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Token oluştur ve cookie'ye ayarla
    token_data = {
        "sub": user.id,
        "username": user.username,
        "pwd": password_stamp(user.hashed_password),
    }
    access_token = create_access_token(token_data)
    _set_auth_cookie(response, access_token)

    return UserResponse.model_validate(user)


@router.post("/login", response_model=UserResponse)
def login(credentials: UserLogin, response: Response, db: Session = Depends(get_db)):
    """Kullanıcı doğrulama ve cookie ile token döndür"""
    # Kullanıcı adı veya e-posta ile kullanıcıyı bul
    user = (
        db.query(User)
        .filter(
            or_(
                User.username == credentials.username,
                User.email == credentials.username,
            )
        )
        .first()
    )

    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Geçersiz kullanıcı adı veya şifre",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Hesap devre dışı"
        )

    # Son giriş zamanını güncelle
    user.last_login = datetime.utcnow()
    db.commit()

    # Token oluştur ve cookie'ye ayarla
    token_data = {
        "sub": user.id,
        "username": user.username,
        "pwd": password_stamp(user.hashed_password),
    }
    access_token = create_access_token(token_data)
    _set_auth_cookie(response, access_token)

    return UserResponse.model_validate(user)


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Mevcut kullanıcı bilgisini getir"""
    return UserResponse.model_validate(current_user)


def _attached_user(db: Session, current_user: User) -> User:
    user = db.query(User).filter(User.id == current_user.id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Geçersiz kimlik bilgileri",
        )
    return user


@router.put("/me", response_model=UserResponse)
def update_profile(
    update_data: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Kullanıcı profilini güncelle"""
    user = _attached_user(db, current_user)
    if update_data.username and update_data.username != user.username:
        existing = (
            db.query(User)
            .filter(User.username == update_data.username, User.id != user.id)
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Bu kullanıcı adı zaten kullanılıyor",
            )
        user.username = update_data.username

    if update_data.email and update_data.email != user.email:
        existing = (
            db.query(User)
            .filter(User.email == update_data.email, User.id != user.id)
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Bu e-posta adresi zaten kullanılıyor",
            )
        user.email = update_data.email

    db.commit()
    db.refresh(user)
    invalidate_user_cache(user.id)

    return UserResponse.model_validate(user)


@router.post("/change-password")
def change_password(
    password_data: ChangePasswordRequest,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Kullanıcı şifresini değiştir"""
    user = _attached_user(db, current_user)
    if not verify_password(
        password_data.current_password, user.hashed_password
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Mevcut şifre yanlış"
        )

    user.hashed_password = get_password_hash(password_data.new_password)
    db.commit()
    invalidate_user_cache(user.id)
    access_token = create_access_token(
        {
            "sub": user.id,
            "username": user.username,
            "pwd": password_stamp(user.hashed_password),
        }
    )
    _set_auth_cookie(response, access_token)

    return {"message": "Şifre başarıyla değiştirildi"}


@router.post("/logout")
async def logout(response: Response):
    """Auth cookie temizleyerek çıkış yap"""
    _clear_auth_cookie(response)
    return {"message": "Oturum kapatıldı"}
