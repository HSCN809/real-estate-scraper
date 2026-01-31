# -*- coding: utf-8 -*-
"""
Database connection configuration for SQLite
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Database file path - relative to Backend folder
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATABASE_PATH = os.path.join(BACKEND_DIR, "real_estate.db")
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
