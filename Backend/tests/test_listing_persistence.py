"""Batch listing persistence and price history regressions."""

import os
import sys

import pytest
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.orm import Session

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from database import crud
from database.models import Base, Listing, Location, PriceHistory, ScrapeSession
from scrapers.emlakjet.persist import save_listings_to_db as save_emlakjet
from scrapers.hepsiemlak.persist import save_listings_to_db as save_hepsiemlak


@pytest.fixture
def db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    try:
        with Session(engine, autoflush=False) as session:
            yield session
    finally:
        engine.dispose()


@pytest.mark.parametrize("save", [save_emlakjet, save_hepsiemlak])
def test_writers_bulk_load_urls_and_locations_and_preserve_price_history(db, save):
    db.add_all(
        ScrapeSession(id=i, platform="fixture", kategori="konut", ilan_tipi="satilik")
        for i in (1, 2)
    )
    db.commit()

    selects = []

    @event.listens_for(db.bind, "before_cursor_execute")
    def record_select(conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith("SELECT"):
            selects.append(statement)

    first = {
        "ilan_linki": "https://example.invalid/first",
        "baslik": "İlk ilan",
        "fiyat": "100",
        "lokasyon": " Ankara / Çankaya ",
    }
    second = {
        "ilan_url": "https://example.invalid/second",
        "baslik": "İkinci ilan",
        "fiyat": "200",
        "il": "Ankara ",
        "ilce": " Çankaya",
    }
    assert save(
        db,
        [first, second],
        "fixture",
        "konut",
        "satilik",
        alt_kategori="daire",
        scrape_session_id=1,
    ) == (2, 0, 0)
    assert len(selects) <= 2

    selects.clear()
    revised = {**second, "fiyat": "250", "baslik": "İkinci ilan güncel"}
    assert save(
        db, [first, revised], "fixture", "konut", "satilik", scrape_session_id=2
    ) == (0, 1, 1)
    assert len(selects) == 1
    assert save(
        db, [first, revised], "fixture", "konut", "satilik", scrape_session_id=2
    ) == (0, 0, 2)

    location = db.scalars(select(Location)).one()
    assert (location.il, location.ilce, location.mahalle) == ("Ankara", "Çankaya", None)
    listings = db.scalars(select(Listing).order_by(Listing.id)).all()
    assert [listing.location_id for listing in listings] == [location.id, location.id]
    assert [listing.scrape_session_id for listing in listings] == [2, 2]
    assert [listing.alt_kategori for listing in listings] == ["daire", "daire"]
    assert listings[1].baslik == "İkinci ilan güncel"
    history = db.scalars(select(PriceHistory)).one()
    assert (history.listing_id, history.old_price, history.new_price) == (
        listings[1].id,
        200,
        250,
    )
    assert (history.price_change, history.price_change_percent) == (50, 25)


@pytest.mark.parametrize("batch_size", [1, 500])
def test_batch_preserves_order_for_repeated_urls_and_creates_url_less_listings(
    db, monkeypatch, batch_size
):
    monkeypatch.setattr(crud, "_LISTING_BATCH_SIZE", batch_size)
    first = {
        "ilan_url": "https://example.invalid/repeated",
        "fiyat": "100",
        "lokasyon": "Bursa, Nilüfer",
    }
    second = {**first, "fiyat": "130", "lokasyon": "İstanbul, Kadıköy"}
    third = {**first, "fiyat": "110"}
    no_url = {"baslik": "Bağlantısız", "il": "Bursa", "ilce": "Nilüfer"}
    batch = [first, second, third, third, no_url, no_url]
    assert crud.upsert_listings(db, batch, "fixture", "konut", "satilik") == (3, 2, 1)
    db.commit()

    listing = db.scalars(select(Listing).where(Listing.ilan_url.is_not(None))).one()
    assert (listing.fiyat, listing.location.il, listing.location.ilce) == (
        110,
        "Bursa",
        "Nilüfer",
    )
    history = db.scalars(select(PriceHistory).order_by(PriceHistory.id)).all()
    assert [(row.old_price, row.new_price) for row in history] == [
        (100, 130),
        (130, 110),
    ]
    assert {row.listing_id for row in history} == {listing.id}
    assert db.scalar(select(func.count()).select_from(Listing)) == 3
    assert db.scalar(select(func.count()).select_from(Location)) == 1


def test_batch_leaves_transaction_under_callers_control(db):
    row = {"ilan_url": "https://example.invalid/rollback", "il": "Bursa"}
    assert crud.upsert_listings(db, [row], "fixture", "konut", "satilik") == (1, 0, 0)
    db.rollback()
    assert db.scalar(select(func.count()).select_from(Listing)) == 0
    assert db.scalar(select(func.count()).select_from(Location)) == 0


def test_selenium_scrapers_skip_retaining_listings_when_db_attached(db, monkeypatch):
    import types
    from unittest.mock import MagicMock

    monkeypatch.setitem(
        sys.modules,
        "undetected_chromedriver",
        types.ModuleType("undetected_chromedriver"),
    )

    from scrapers.emlakjet.main import EmlakJetScraper
    import scrapers.hepsiemlak.main as he_main

    fake_driver = MagicMock()
    fake_driver.current_url = "https://www.emlakjet.com/satilik-konut/istanbul"
    sample = [
        {
            "baslik": "Test",
            "fiyat": "1.000.000 TL",
            "ilan_url": "https://www.emlakjet.com/ilan/1",
            "ilan_linki": "https://www.hepsiemlak.com/ilan/1",
            "il": "İstanbul",
            "ilce": "Kadıköy",
        }
    ]

    ej = EmlakJetScraper(driver=fake_driver, category="konut", listing_type="satilik")
    ej.db = db
    ej.config.wait_between_pages = 0
    ej.scrape_current_page = lambda: list(sample)
    ej.scrape_pages("https://www.emlakjet.com/satilik-konut/istanbul", max_pages=2)
    assert ej.total_scraped_count == 2
    assert ej.all_listings == []

    he = he_main.HepsiemlakScraper(
        driver=fake_driver, category="konut", listing_type="satilik"
    )
    he.db = db
    he.select_single_city = lambda city: True
    he.get_total_pages = lambda: 2
    he._wait_for_listing_ready = lambda timeout=20: True
    he.random_medium_wait = lambda: 0
    he.random_long_wait = lambda: 0
    he.scrape_current_page = lambda fallback_city=None, fallback_district=None: list(sample)
    monkeypatch.setattr(he_main, "save_listings_to_db", lambda *a, **kw: (1, 0, 0))
    res = he.scrape_city("İstanbul", max_pages=2, api_mode=True)
    assert he.total_scraped_count == 2
    assert res == []
