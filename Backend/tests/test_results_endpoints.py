"""Result pagination and chart summaries through the API."""

import os
import sys
from datetime import datetime
from threading import get_ident

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
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
    app.state.sql_queries = []

    @app.middleware("http")
    async def record_loop_thread(request, call_next):
        app.state.loop_thread = get_ident()
        return await call_next(request)

    @event.listens_for(engine, "before_cursor_execute")
    def record_sql(_conn, _cursor, statement, _params, _context, _many):
        app.state.sql_queries.append((statement, get_ident()))

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


def test_results_pagination_counts_groups_without_a_window(client):
    response = client.get("/api/v1/results?limit=2&page=99")

    assert response.status_code == 200
    payload = response.json()
    assert (payload["page"], payload["pages"], payload["total"]) == (2, 2, 4)
    bursa = next(row for row in payload["items"] if row["city"] == "Bursa")
    assert bursa["district"] is None and bursa["subtype"] is None
    assert (bursa["count"], bursa["avg_price"]) == (1, 600)

    statements = [
        " ".join(statement.upper().split())
        for statement, _thread in client.app.state.sql_queries
    ]
    assert len(statements) == 1
    grouped, limited = statements[0].split(" LIMIT ", 1)
    assert grouped.count(" GROUP BY ") == 1
    assert "COUNT(*) AS TOTAL" in grouped
    assert " GROUP BY " not in limited
    assert " OVER " not in statements[0]


def test_results_keep_empty_page_metadata_with_filters(client):
    response = client.get("/api/v1/results?category=devremulk&page=99&limit=2")

    assert response.status_code == 200
    assert response.json() == {
        "items": [],
        "page": 1,
        "limit": 2,
        "pages": 0,
        "total": 0,
    }


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


def test_result_filters_return_overview_from_the_same_group_query(client):
    overview = client.get("/api/v1/results/overview").json()
    last_scrape = client.get("/api/v1/stats").json()["last_scrape"]
    client.app.state.sql_queries.clear()

    response = client.get("/api/v1/results/filters?include_overview=true")

    assert response.status_code == 200
    assert response.json()["overview"] == overview
    assert response.json()["last_scrape"] == last_scrape
    statements = [query for query, _thread in client.app.state.sql_queries]
    assert len(statements) == 2
    assert sum("GROUP BY" in query for query in statements) == 1

    filters_only = client.get("/api/v1/results/filters").json()
    assert "overview" not in filters_only
    assert filters_only["last_scrape"] == last_scrape


def test_listing_statistics_queries_run_off_the_event_loop(client):
    response = client.get("/api/v1/analytics/stats")

    assert response.status_code == 200
    assert response.json()["total_listings"] == 5
    assert client.app.state.sql_queries
    assert all(
        thread != client.app.state.loop_thread
        for _query, thread in client.app.state.sql_queries
    )


def test_sql_price_stats_match_python_reference_on_edge_cases():
    from database import crud

    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)

    cases = [
        ("single", [1_250_000.0]),
        ("equal", [500_000.0, 500_000.0, 500_000.0, 500_000.0]),
        ("multi", [100_000.0, 250_000.0, 400_000.0, 750_000.0, 1_200_000.0, 3_500_000.0, 8_000_000.0]),
    ]

    with Session(engine) as db:
        for idx, (city_name, prices) in enumerate(cases):
            loc = Location(il=city_name, ilce="Merkez")
            db.add(loc)
            db.flush()
            for j, price in enumerate(prices):
                db.add(
                    Listing(
                        baslik=f"{city_name}-{j}",
                        platform="hepsiemlak",
                        kategori="konut",
                        ilan_tipi="satilik",
                        location_id=loc.id,
                        fiyat=price,
                        ilan_url=f"https://example.com/{idx}/{j}",
                    )
                )
        db.commit()

        for city_name, prices in cases:
            expected_stats, expected_ranges = crud.compute_price_stats_and_ranges(
                sorted(prices)
            )
            result = crud.get_city_analytics(db, city_name)
            assert result["stats"] == expected_stats
            assert result["price_ranges"] == expected_ranges

    engine.dispose()


def test_gzip_and_cache_control_headers():
    from main import app

    app.dependency_overrides[get_current_user] = lambda: None
    try:
        with TestClient(app) as real_client:
            cats = real_client.get("/api/v1/config/categories")
            assert cats.status_code == 200
            assert cats.headers.get("cache-control") == "public, max-age=86400"

            idx = real_client.get(
                "/api/v1/districts/index", headers={"Accept-Encoding": "gzip"}
            )
            assert idx.status_code == 200
            assert idx.headers.get("cache-control") == "public, max-age=86400"
            assert idx.headers.get("content-encoding") == "gzip"
    finally:
        app.dependency_overrides.clear()


def test_results_read_cache_hits_and_invalidates_on_delete(client):
    assert client.get("/api/v1/results?limit=2").status_code == 200
    assert client.get("/api/v1/stats").status_code == 200
    client.app.state.sql_queries.clear()

    cached_results = client.get("/api/v1/results?limit=2")
    cached_stats = client.get("/api/v1/stats")
    assert cached_results.status_code == 200
    assert cached_stats.status_code == 200
    assert client.app.state.sql_queries == []

    deleted = client.delete("/api/v1/listings/group", params={"city": "Bursa"})
    assert deleted.status_code == 200
    refreshed = client.get("/api/v1/results?limit=2").json()
    assert refreshed["total"] == 3


def test_filtered_city_locations_cache_reuses_distinct_lookup(client):
    assert client.get("/api/v1/results?city=Ankara&page=1&limit=1").status_code == 200
    client.app.state.sql_queries.clear()

    second = client.get("/api/v1/results?city=Ankara&page=2&limit=1")
    assert second.status_code == 200
    statements = [statement.upper() for statement, _ in client.app.state.sql_queries]
    assert not any("SELECT DISTINCT" in stmt for stmt in statements)
