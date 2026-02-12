# -*- coding: utf-8 -*-
"""Emlak Kazıyıcı - Backend API, FastAPI uygulama tanımı"""

import sys
import os
import logging
import time
from contextlib import asynccontextmanager

# Import'lar için mevcut dizini yola ekle
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.endpoints import router as api_router
from auth.router import router as auth_router

# Veritabanı başlatma
from database.connection import engine, DATABASE_URL
from database.models import Base

# Loglama ayarla
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_database(max_retries=5, retry_delay=3):
    """Veritabanı tablolarını yoksa oluşturur (yeniden deneme destekli)"""
    for attempt in range(1, max_retries + 1):
        try:
            Base.metadata.create_all(bind=engine)
            if DATABASE_URL and DATABASE_URL.startswith('postgresql'):
                logger.info("PostgreSQL veritabanina baglandi")
            else:
                logger.info("SQLite veritabani kullaniliyor")
            return
        except Exception as e:
            if attempt < max_retries:
                logger.warning(f"Veritabani baglantisi basarisiz (deneme {attempt}/{max_retries}): {e}")
                time.sleep(retry_delay)
            else:
                logger.error(f"Veritabani baglantisi {max_retries} denemede kurulamadi: {e}")
                raise

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Başlatma
    init_database()
    yield
    # Kapatma

# FastAPI uygulamasını başlat
app = FastAPI(
    title="Real Estate Scraper API",
    description="API for EmlakJet and HepsiEmlak scrapers",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS - çerez kimlik doğrulaması için açık origin'ler gerekli
ALLOWED_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")


@app.get("/")
async def root():
    return {"message": "Real Estate Scraper API is running"}
