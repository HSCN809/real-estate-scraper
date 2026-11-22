"""Result pagination and chart summaries through the API."""

import os
import sys
from datetime import datetime

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from api.endpoints import router
from auth.dependencies import get_current_user
from database.connection import get_db
from database.models import Base, Listing, Location


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        central = Location(il=" Ankara ", ilce="Çankaya")
        north = Location(il=" Ankara ", ilce="Keçiören")
        bursa = Location(il="Bursa")
        unknown = Location(il="Belirtilmemiş", ilce="-")
        for location, category, price in (
            (central, "konut", 100),
            (central, "konut", 300),
            (north, "konut", 200),
            (bursa, "arsa", 600),
            (unknown, "konut", 0),
            (None, "konut", 990),
        ):
            db.add(
                Listing(
                    baslik="Test ilanı",
                    platform="emlakjet",
                    kategori=category,
                    ilan_tipi="satilik",
                    alt_kategori="bahce_kati" if category == "konut" else None,
                    location=location,
                    fiyat=price,
                    created_at=datetime(2026, 1, 1, 22),
                    updated_at=datetime(2026, 1, 1, 22),
                )
            )
        db.commit()

    def get_test_db():
        with Session(engine) as db:
            yield db

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_db] = get_test_db
    app.dependency_overrides[get_current_user] = lambda: None
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        engine.dispose()


def test_results_paginate_stably_across_equal_timestamps(client):
    first = client.get("/api/v1/results?limit=2").json()
    second = client.get("/api/v1/results?limit=2&page=2").json()
    assert first["total"] == 4
    assert (first["pages"], first["page"], second["page"]) == (2, 1, 2)
    assert len({row["id"] for row in first["items"] + second["items"]}) == 4
    assert client.get("/api/v1/results?limit=101").status_code == 422
    assert client.get("/api/v1/results?limit=2&page=99").json() == second


def test_result_filters_and_overview_cover_more_than_the_current_page(client):
    filters = [("city", "Ankara"), ("city", "Bursa"), ("subtype", "Bahce Kati")]
    page = client.get("/api/v1/results", params=[*filters, ("limit", 1)]).json()
    assert page["total"] == 2
    assert page["items"][0]["city"] == "Ankara"
    overview = client.get("/api/v1/results/overview", params=filters).json()
    assert overview["cities"] == [{"city": "Ankara", "count": 3}]
    assert overview["history"] == [{"date": "2026-01-02", "count": 3}]
    options = client.get("/api/v1/results/filters").json()
    assert options["locations"]["Ankara"] == ["Keçiören", "Çankaya"]
    assert options["locations"]["Bilinmiyor"] == []
    assert (options["total_groups"], options["total_listings"]) == (4, 5)


def test_prices_return_aggregates_and_cover_every_valid_price(client):
    response = client.get("/api/v1/analytics/prices")
    assert response.status_code == 200
    data = response.json()
    assert "prices" not in data
    assert data["summary"] == {
        "total_count": 4,
        "avg_price": 300,
        "min_price": 100,
        "max_price": 600,
    }
    assert data["cities"][0] == {"city": "Bursa", "avg_price": 600}
    assert data["platforms"] == [{"platform": "Emlakjet", "avg_price": 300}]
    assert sum(bucket["count"] for bucket in data["histogram"]) == 4
    filtered = client.get(
        "/api/v1/analytics/prices", params={"category": "Arsa", "city": "Bursa"}
    ).json()
    assert filtered["histogram"] == [{"min": 600, "max": 600, "count": 1}]
    empty = client.get("/api/v1/analytics/prices?city=Yokşehir").json()
    assert empty["summary"]["total_count"] == 0
    assert empty["histogram"] == []
