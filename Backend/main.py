"""Emlak Kazıyıcı - Backend API, FastAPI uygulama tanımı"""

import logging
import os
import sys
import time
from contextlib import asynccontextmanager

# Import'lar için mevcut dizini yola ekle
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api.endpoints import router as api_router
from auth.router import router as auth_router
from core.task_status import get_redis_client
from database import crud

# Veritabani baslatma
from database.connection import DATABASE_URL, SessionLocal, engine
from database.models import Base
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from sqlalchemy import text

# Loglama ayarla
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def init_database(max_retries=5, retry_delay=3):
    """Veritabani tablolari yoksa olusturur (yeniden deneme destekli)."""
    for attempt in range(1, max_retries + 1):
        try:
            Base.metadata.create_all(bind=engine)
            if DATABASE_URL and DATABASE_URL.startswith("postgresql"):
                logger.info("PostgreSQL veritabanina baglandi")
            else:
                logger.info("SQLite veritabani kullaniliyor")
            return
        except Exception as e:
            if attempt < max_retries:
                logger.warning(
                    f"Veritabani baglantisi basarisiz (deneme {attempt}/{max_retries}): {e}"
                )
                time.sleep(retry_delay)
            else:
                logger.error(
                    f"Veritabani baglantisi {max_retries} denemede kurulamadi: {e}"
                )
                raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Baslatma
    init_database()
    db = SessionLocal()
    try:
        updated = crud.normalize_legacy_scrape_session_statuses(db)
        if updated:
            db.commit()
            logger.info("Normalized %s legacy scrape session statuses", updated)
    finally:
        db.close()
    yield
    # Kapatma


# FastAPI uygulamasini baslat
app = FastAPI(
    title="Real Estate Scraper API",
    description="API for EmlakJet and HepsiEmlak scrapers",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS - cerez kimlik dogrulamasi icin acik origin'ler gerekli
ALLOWED_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

app.include_router(api_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")


@app.get("/")
async def root():
    return {"message": "Real Estate Scraper API is running"}


@app.get("/health")
def health(response: Response):
    """Docker healthcheck: DB ve Redis erişilebilir mi (hata detayı dışarı verilmez)."""
    checks = {}
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:
        logger.warning("Health check: database unavailable: %s", exc)
        checks["database"] = "error"
    try:
        get_redis_client().ping()
        checks["redis"] = "ok"
    except Exception as exc:
        logger.warning("Health check: redis unavailable: %s", exc)
        checks["redis"] = "error"
    healthy = all(value == "ok" for value in checks.values())
    if not healthy:
        response.status_code = 503
    return {"status": "ok" if healthy else "error", **checks}
