# -*- coding: utf-8 -*-
"""
Database connection configuration for SQLite
Environment variable destekli konfigürasyon
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Database file path - Environment variable veya varsayılan yol
# Docker için: DATABASE_PATH=/app/database/real_estate.db
DATABASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DB_PATH = os.path.join(DATABASE_DIR, "real_estate.db")
DATABASE_PATH = os.getenv('DATABASE_PATH', DEFAULT_DB_PATH)

# Veritabanı dizininin var olduğundan emin ol
os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)

DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

# Create engine with SQLite-specific settings
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # Required for SQLite with FastAPI
    echo=False  # Set to True for SQL debugging
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """
    Dependency function for FastAPI endpoints.
    Yields a database session and ensures cleanup.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db_session():
    """
    Get a database session for non-FastAPI use (e.g., scrapers).
    Remember to close the session when done.
    """
    return SessionLocal()
