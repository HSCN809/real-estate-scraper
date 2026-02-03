# -*- coding: utf-8 -*-
"""
Database connection configuration
PostgreSQL (Docker) veya SQLite (lokal) destekli
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Database URL - PostgreSQL veya SQLite
# Docker için: DATABASE_URL=postgresql://user:pass@host:port/dbname
# Lokal için: DATABASE_URL belirtilmezse SQLite kullanılır
DATABASE_URL = os.getenv('DATABASE_URL')

if DATABASE_URL:
    # PostgreSQL (Docker)
    engine = create_engine(
        DATABASE_URL,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,  # Bağlantı kontrolü
        echo=False
    )
else:
    # SQLite (Lokal geliştirme)
    DATABASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DATABASE_PATH = os.path.join(DATABASE_DIR, "real_estate.db")
    DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=False
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
