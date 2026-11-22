"""Listing query counts and Excel request concurrency."""

import asyncio
import io
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest
from anyio.to_process import run_sync
from fastapi import FastAPI
from fastapi.testclient import TestClient
from openpyxl import load_workbook
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from api import endpoints
from auth.dependencies import get_current_user
from database.connection import get_db
from database.models import Base, Listing, Location


@pytest.fixture
def listing_api():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        for city in ("Ankara", "Bursa", None):
            db.add(
                Listing(
                    baslik=city or "Konumsuz",
                    platform="emlakjet",
                    kategori="konut",
                    ilan_tipi="satilik",
                    location=Location(il=city) if city else None,
                )
            )
        db.commit()

    selects = []

    @event.listens_for(engine, "before_cursor_execute")
    def record_select(conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith("SELECT"):
            selects.append(statement)

    def get_test_db():
        with Session(engine) as db:
            yield db

    app = FastAPI()
    app.include_router(endpoints.router, prefix="/api/v1")
    app.dependency_overrides[get_db] = get_test_db
    app.dependency_overrides[get_current_user] = lambda: None

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    try:
        with TestClient(app) as client:
            yield client, selects
    finally:
        engine.dispose()


@pytest.mark.parametrize(
    ("path", "items_key", "cities"),
    [
        ("/listings", "items", {"Ankara", "Bursa", None}),
        ("/listings/preview?city=Ankara", "data", {"Ankara"}),
    ],
)
def test_listings_batch_load_locations(listing_api, path, items_key, cities):
    client, selects = listing_api
    response = client.get(f"/api/v1{path}")
    assert response.status_code == 200
    assert {item["il"] for item in response.json()[items_key]} == cities
    assert response.json()["total"] == len(cities)
    assert len(selects) <= 3


def test_excel_export_allows_concurrent_health_request(listing_api, monkeypatch):
    client, selects = listing_api
    writing = Event()
    release = Event()

    async def pause_writer(writer, *args, **kwargs):
        writing.set()
        assert await asyncio.to_thread(release.wait, 10)
        assert await run_sync(os.getpid) != os.getpid()
        return await run_sync(writer, *args, **kwargs)

    monkeypatch.setattr(endpoints, "run_in_process", pause_writer, raising=False)
    with ThreadPoolExecutor(max_workers=2) as executor:
        export = executor.submit(client.post, "/api/v1/export/excel")
        try:
            assert writing.wait(10)
            health = executor.submit(client.get, "/health")
            assert health.result(timeout=2).status_code == 200
        finally:
            release.set()
        response = export.result(timeout=10)

    assert response.status_code == 200
    assert response.headers["content-disposition"].startswith("attachment;")
    workbook = load_workbook(io.BytesIO(response.content), read_only=True)
    try:
        headers, *rows = workbook.active.values
    finally:
        workbook.close()
    assert {row[headers.index("İl")] for row in rows} == {"Ankara", "Bursa", None}
    assert len(selects) <= 3
