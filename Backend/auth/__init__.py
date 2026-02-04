# -*- coding: utf-8 -*-
"""
Authentication module for Real Estate Scraper
"""

from .security import verify_password, get_password_hash, create_access_token, decode_token
from .dependencies import get_current_user, get_optional_user
from .router import router as auth_router

__all__ = [
    'verify_password',
    'get_password_hash',
    'create_access_token',
    'decode_token',
    'get_current_user',
    'get_optional_user',
    'auth_router'
]
