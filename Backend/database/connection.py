"""Veritabanı bağlantı konfigürasyonu"""

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

def normalize_database_url(url: str) -> str:
    """Normalize PostgreSQL URLs to use the psycopg v3 SQLAlchemy dialect."""
    if url.startswith("postgresql+psycopg2://"):
        return "postgresql+psycopg://" + url[len("postgresql+psycopg2://") :]
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://") :]
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://") :]
    return url


# Veritabanı URL - PostgreSQL veya SQLite
DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    DATABASE_URL = normalize_database_url(DATABASE_URL)
    # PostgreSQL (Docker)
    engine = create_engine(
        DATABASE_URL,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,  # Bağlantı kontrolü
        echo=False,
    )
else:
    # SQLite (Lokal geliştirme)
    DATABASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DATABASE_PATH = os.path.join(DATABASE_DIR, "real_estate.db")
    DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

    engine = create_engine(
        DATABASE_URL, connect_args={"check_same_thread": False}, echo=False
    )

# Oturum fabrikası
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """FastAPI endpoint'leri için veritabanı oturumu"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db_session():
    """FastAPI dışı kullanım için veritabanı oturumu"""
    return SessionLocal()
