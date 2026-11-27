"""Tests for database URL normalization and psycopg v3 dialect wiring."""

from sqlalchemy import create_engine

from database.connection import normalize_database_url


def test_normalize_database_url_converts_legacy_and_bare_postgres_urls():
    assert (
        normalize_database_url("postgresql://user:pass@host:5432/db")
        == "postgresql+psycopg://user:pass@host:5432/db"
    )
    assert (
        normalize_database_url("postgres://user:pass@host:5432/db")
        == "postgresql+psycopg://user:pass@host:5432/db"
    )
    assert (
        normalize_database_url("postgresql+psycopg2://user:pass@host:5432/db")
        == "postgresql+psycopg://user:pass@host:5432/db"
    )
    assert (
        normalize_database_url("postgresql+psycopg://user:pass@host:5432/db")
        == "postgresql+psycopg://user:pass@host:5432/db"
    )
    assert normalize_database_url("sqlite:///./real_estate.db") == "sqlite:///./real_estate.db"


def test_sqlalchemy_creates_psycopg3_engine():
    engine = create_engine("postgresql+psycopg://user:pass@localhost:5432/db")
    try:
        assert engine.dialect.name == "postgresql"
        assert engine.dialect.driver == "psycopg"
    finally:
        engine.dispose()
