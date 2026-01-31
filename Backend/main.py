# -*- coding: utf-8 -*-
"""
Real Estate Scraper - Backend API
FastAPI application definition
"""

import sys
import os

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.endpoints import router as api_router

# Database initialization
from database.connection import engine
from database.models import Base

def init_database():
    """Create database tables if they don't exist"""
    Base.metadata.create_all(bind=engine)

# Initialize database on startup
init_database()

# Initialize FastAPI App
app = FastAPI(
    title="Real Estate Scraper API",
    description="API for EmlakJet and HepsiEmlak scrapers",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    return {"message": "Real Estate Scraper API is running"}
