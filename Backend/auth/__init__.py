"""
Authentication module for Real Estate Scraper
"""

from .dependencies import get_current_user, get_optional_user
from .router import router as auth_router
from .security import (
    create_access_token,
    decode_token,
    get_password_hash,
    verify_password,
)

__all__ = [
    "auth_router",
    "create_access_token",
    "decode_token",
    "get_current_user",
    "get_optional_user",
    "get_password_hash",
    "verify_password",
]
