"""Veritabani CRUD islemleri."""

import hashlib
import json
import re
from collections import Counter
from datetime import datetime
from typing import Any, cast

from core.task_status import (
    SCRAPE_SESSION_STATUS_COMPLETED,
    SCRAPE_SESSION_STATUS_RUNNING,
    SCRAPE_SESSION_STATUS_VALUES,
    normalize_scrape_session_status,
)
from sqlalchemy import func, select, true, tuple_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload
from utils.timezone import format_istanbul, latest_datetime, now_utc_naive

from .models import FailedPage, Listing, Location, PriceHistory, ScrapeSession

# ============== Hash Yardımcıları ==============


def compute_content_hash(data: dict[str, Any]) -> str:
    """İlan içerik hash'i hesapla (fiyat hariç)"""
    # Hash'e dahil edilecek alanlar (fiyat hariç)
    hash_fields = [
        "baslik",
        "oda_sayisi",
        "metrekare",
        "bina_yasi",
        "kat",
        "arsa_metrekare",
        "imar_durumu",
        "arsa_tipi",
        "isyeri_tipi",
        "tesis_tipi",
        "yatak_sayisi",
        "emlak_ofisi",
        "tip",
    ]

    # Icerik string'ini olustur
    content_parts = []
    for field in hash_fields:
        value = data.get(field)
        if value is not None:
            content_parts.append(f"{field}:{value}")

    # Detaylar varsa dahil et
    details = data.get("details")
    if details and isinstance(details, dict):
        content_parts.append(f"details:{json.dumps(details, sort_keys=True)}")

    content_str = "|".join(sorted(content_parts))
    return hashlib.md5(content_str.encode("utf-8"), usedforsecurity=False).hexdigest()


# ============== Lokasyon CRUD ==============


def get_or_create_location(
    db: Session, il: str, ilce: str | None = None, mahalle: str | None = None
) -> Location:
    """Mevcut lokasyonu getir veya yeni olustur."""
    # Girdileri normalize et
    il = il.strip() if il else None
    ilce = ilce.strip() if ilce else None
    mahalle = mahalle.strip() if mahalle else None

    if not il:
        il = "Belirtilmemiş"

    # Mevcut olani bulmaya calis
    location = (
        db.query(Location)
        .filter(
            Location.il == il,
            Location.ilce == ilce if ilce else Location.ilce.is_(None),
            Location.mahalle == mahalle if mahalle else Location.mahalle.is_(None),
        )
        .first()
    )

    if location:
        return location

    # Yeni olustur
    location = Location(il=il, ilce=ilce, mahalle=mahalle)
    db.add(location)

    try:
        db.flush()  # Commit etmeden ID al
    except IntegrityError:
        db.rollback()
        # Yaris durumu - yeni olusturulani getir
        location = (
            db.query(Location)
            .filter(
                Location.il == il,
                Location.ilce == ilce if ilce else Location.ilce.is_(None),
                Location.mahalle == mahalle if mahalle else Location.mahalle.is_(None),
            )
            .first()
        )

    return location


def get_all_cities(db: Session) -> list[str]:
    """Tum benzersiz sehir adlarini getir."""
    result = db.query(Location.il).distinct().order_by(Location.il).all()
    return [r[0] for r in result if r[0]]


def get_districts_by_city(db: Session, city: str) -> list[str]:
    """Bir sehrin tum ilcelerini getir."""
    result = (
        db.query(Location.ilce)
        .filter(Location.il == city, Location.ilce.isnot(None))
        .distinct()
        .order_by(Location.ilce)
        .all()
    )
    return [r[0] for r in result if r[0]]


# ============== İlan CRUD ==============


def parse_price(price_str: str) -> float | None:
    """Türkçe fiyat metnini float'a çevir"""
    if not price_str or str(price_str).strip().lower() in [
        "belirtilmemiş",
        "belirtilmemis",
        "",
    ]:
        return None

    try:
        val_str = str(price_str).strip()
        val_str = re.sub(r"\s+", "", val_str)
        val_str = val_str.replace("TL", "").replace("₺", "")

        # Turkce sayi formatini isle
        if "," in val_str and "." in val_str:
            val_str = val_str.replace(".", "").replace(",", ".")
        elif "." in val_str and val_str.count(".") > 1 or "." in val_str and len(val_str.split(".")[-1]) == 3:
            val_str = val_str.replace(".", "")
        elif "," in val_str:
            val_str = val_str.replace(",", ".")

        price = float(val_str)
        return price if price > 0 else None
    except (ValueError, TypeError):
        return None


_LocationKey = tuple[str, str | None, str | None]
_LISTING_BATCH_SIZE = 500
_LOCATION_BATCH_SIZE = 250


def _listing_url(data: dict[str, Any]) -> str | None:
    return data.get("ilan_linki") or data.get("ilan_url")


def _listing_location_key(data: dict[str, Any]) -> _LocationKey:
    il = data.get("il")
    ilce = data.get("ilce")
    mahalle = data.get("mahalle")

    if not il or il == "Belirtilmemiş":
        # Fallback: lokasyon alanından parse et
        lokasyon = data.get("lokasyon", "")
        if lokasyon:
            # EmlakJet formati: "İstanbul / Kadıköy / Caferağa"
            # HepsiEmlak formatı: "İstanbul, Kadıköy"
            if "/" in lokasyon:
                parts = [p.strip() for p in lokasyon.split("/")]
            else:
                parts = [p.strip() for p in lokasyon.split(",")]
            il = parts[0] if len(parts) > 0 else None
            if not ilce and len(parts) > 1:
                ilce = parts[1]
            if not mahalle and len(parts) > 2:
                mahalle = parts[2]
    return (
        (il or "").strip() or "Belirtilmemiş",
        (ilce or "").strip() or None,
        (mahalle or "").strip() or None,
    )


def _new_listing(
    data: dict[str, Any],
    location: Location,
    platform: str,
    kategori: str,
    ilan_tipi: str,
    alt_kategori: str | None,
    scrape_session_id: int | None,
) -> Listing:
    # Fiyati ayristir
    fiyat_text = data.get("fiyat", "")
    fiyat = parse_price(fiyat_text)

    # Kategoriye özel detayları çıkar
    details = {}
    detail_fields = [
        "oda_sayisi",
        "metrekare",
        "bina_yasi",
        "kat",
        "arsa_metrekare",
        "metrekare_fiyat",
        "imar_durumu",
        "arsa_tipi",
        "isyeri_tipi",
        "tesis_tipi",
        "yatak_sayisi",
        "otel_tipi",
        "tip",
        "one_cikan",
        "yeni",
    ]
    for field in detail_fields:
        if data.get(field):
            details[field] = data[field]

    # Ilan tarihini ayristir
    ilan_tarihi = None
    if data.get("ilan_tarihi"):
        try:
            # Yaygın formatları dene
            date_str = str(data["ilan_tarihi"]).strip()
            for fmt in ["%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S"]:
                try:
                    ilan_tarihi = datetime.strptime(date_str, fmt).date()
                    break
                except ValueError:
                    continue
        except Exception:  # nosec
            pass

    # İçerik hash'i hesapla
    content_hash = compute_content_hash(data)

    # Ilan olustur
    return Listing(
        baslik=data.get("baslik", "Başlık Yok"),
        fiyat=fiyat,
        fiyat_text=str(fiyat_text) if fiyat_text else None,
        platform=platform,
        kategori=kategori,
        ilan_tipi=ilan_tipi,
        alt_kategori=alt_kategori,
        location=location,
        ilan_url=_listing_url(data),
        ilan_tarihi=ilan_tarihi,
        emlak_ofisi=data.get("emlak_ofisi"),
        resim_url=data.get("resim_url"),
        details=details if details else None,
        scrape_session_id=scrape_session_id,
        content_hash=content_hash,
    )


def create_listing(
    db: Session,
    data: dict[str, Any],
    platform: str,
    kategori: str,
    ilan_tipi: str,
    alt_kategori: str | None = None,
    scrape_session_id: int | None = None,
) -> tuple[Listing | None, bool]:
    """Yeni ilan olustur, (ilan, yeni_mi) dondur."""
    ilan_url = _listing_url(data)
    if ilan_url and db.query(Listing).filter(Listing.ilan_url == ilan_url).first():
        return None, False

    location = get_or_create_location(db, *_listing_location_key(data))
    listing = _new_listing(
        data, location, platform, kategori, ilan_tipi, alt_kategori, scrape_session_id
    )
    db.add(listing)
    try:
        db.flush()
        return listing, True
    except IntegrityError:
        db.rollback()
        return None, False


def _update_listing(
    db: Session,
    existing: Listing,
    data: dict[str, Any],
    scrape_session_id: int | None,
) -> str:
    # Mevcut ilan bulundu - yeni hash hesapla
    new_content_hash = compute_content_hash(data)
    new_fiyat_text = data.get("fiyat", "")
    new_fiyat = parse_price(new_fiyat_text)

    # Fiyat degisikligi kontrolu
    price_changed = False
    old_price = existing.fiyat
    if new_fiyat is not None and existing.fiyat != new_fiyat:
        price_changed = True

    # Hash kullanarak icerik degisikligi kontrolu
    content_changed = existing.content_hash != new_content_hash

    # Degisiklik yoksa guncellemeyi atla
    if not price_changed and not content_changed:
        existing.scrape_session_id = scrape_session_id
        return "unchanged"

    # Uygunsa fiyat degisikligini kaydet
    if price_changed and old_price is not None and new_fiyat is not None:
        price_change = new_fiyat - old_price
        price_change_percent = (price_change / old_price) * 100 if old_price > 0 else 0

        price_record = PriceHistory(
            listing=existing,
            old_price=old_price,
            new_price=new_fiyat,
            price_change=price_change,
            price_change_percent=round(price_change_percent, 2),
        )
        db.add(price_record)

    # İlanı güncelle
    new_baslik = data.get("baslik")
    if new_baslik:
        existing.baslik = new_baslik
    if new_fiyat is not None:
        existing.fiyat = new_fiyat
        existing.fiyat_text = str(new_fiyat_text) if new_fiyat_text else None

    new_emlak_ofisi = data.get("emlak_ofisi")
    if new_emlak_ofisi:
        existing.emlak_ofisi = new_emlak_ofisi

    new_resim_url = data.get("resim_url")
    if new_resim_url:
        existing.resim_url = new_resim_url

    # Detaylar varsa güncelle
    new_details = {}
    detail_fields = [
        "oda_sayisi",
        "metrekare",
        "bina_yasi",
        "kat",
        "arsa_metrekare",
        "metrekare_fiyat",
        "imar_durumu",
        "arsa_tipi",
        "isyeri_tipi",
        "tesis_tipi",
        "yatak_sayisi",
        "otel_tipi",
        "tip",
        "one_cikan",
        "yeni",
    ]
    for field in detail_fields:
        if data.get(field):
            new_details[field] = data[field]

    if new_details:
        existing.details = {**(existing.details or {}), **new_details}

    # Hash ve meta verileri güncelle
    existing.content_hash = new_content_hash
    existing.updated_at = datetime.utcnow()
    existing.scrape_session_id = scrape_session_id

    return "updated"


def upsert_listing(
    db: Session,
    data: dict[str, Any],
    platform: str,
    kategori: str,
    ilan_tipi: str,
    alt_kategori: str | None = None,
    scrape_session_id: int | None = None,
) -> tuple[Listing | None, str]:
    """İlan upsert - yeniyse ekle, varsa güncelle."""
    url = _listing_url(data)
    if url:
        existing = db.query(Listing).filter(Listing.ilan_url == url).first()
        if existing is not None:
            status = _update_listing(db, existing, data, scrape_session_id)
            if status == "updated":
                db.flush()
            return existing, status

    listing, is_new = create_listing(
        db, data, platform, kategori, ilan_tipi, alt_kategori, scrape_session_id
    )
    return listing, "created" if is_new else "error"


def _load_listing_locations(
    db: Session, location_keys: list[_LocationKey]
) -> dict[_LocationKey, Location]:
    locations: dict[_LocationKey, Location] = {}
    # Treat legacy empty strings and NULL as the same missing district or neighborhood.
    location_tuple = tuple_(
        Location.il,
        func.coalesce(Location.ilce, ""),
        func.coalesce(Location.mahalle, ""),
    )
    for start in range(0, len(location_keys), _LOCATION_BATCH_SIZE):
        keys = [
            (city, district or "", neighborhood or "")
            for city, district, neighborhood in location_keys[
                start : start + _LOCATION_BATCH_SIZE
            ]
        ]
        query = select(Location).where(location_tuple.in_(keys)).order_by(Location.id)
        for location in db.scalars(query):
            locations.setdefault(
                (location.il, location.ilce or None, location.mahalle or None), location
            )
    return locations


def upsert_listings(
    db: Session,
    listings: list[dict],
    platform: str,
    kategori: str,
    ilan_tipi: str,
    alt_kategori: str | None = None,
    scrape_session_id: int | None = None,
) -> tuple[int, int, int]:
    """Upsert in input order and leave the transaction to the caller."""
    if not listings:
        return 0, 0, 0

    db.flush()
    counts: Counter[str] = Counter()
    for start in range(0, len(listings), _LISTING_BATCH_SIZE):
        batch = listings[start : start + _LISTING_BATCH_SIZE]
        urls = [_listing_url(data) for data in batch]
        unique_urls = {url for url in urls if url}
        existing: dict[str, Listing] = {}
        if unique_urls:
            # Serialize updates to existing prices so history uses the current value.
            query = (
                select(Listing)
                .where(Listing.ilan_url.in_(unique_urls))
                .order_by(Listing.ilan_url)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            existing = {listing.ilan_url: listing for listing in db.scalars(query)}

        # Only the first occurrence of a new URL decides its location.
        seen_urls = set(existing)
        keys_by_index = {}
        for index, (data, url) in enumerate(zip(batch, urls)):
            if not url or url not in seen_urls:
                keys_by_index[index] = _listing_location_key(data)
                if url:
                    seen_urls.add(url)
        locations = _load_listing_locations(
            db, list(dict.fromkeys(keys_by_index.values()))
        )

        for index, (data, url) in enumerate(zip(batch, urls)):
            listing = existing.get(url) if url else None
            if listing is not None:
                counts[_update_listing(db, listing, data, scrape_session_id)] += 1
                continue

            key = keys_by_index[index]
            location = locations.get(key)
            if location is None:
                city, district, neighborhood = key
                location = Location(il=city, ilce=district, mahalle=neighborhood)
                locations[key] = location
            listing = _new_listing(
                data,
                location,
                platform,
                kategori,
                ilan_tipi,
                alt_kategori,
                scrape_session_id,
            )
            db.add(listing)
            if url:
                existing[url] = listing
            counts["created"] += 1

        db.flush()

    return counts["created"], counts["updated"], counts["unchanged"]


def get_listings(
    db: Session,
    platform: str | None = None,
    kategori: str | None = None,
    ilan_tipi: str | None = None,
    alt_kategori: str | None = None,
    city: str | None = None,
    district: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    page: int = 1,
    limit: int = 50,
) -> tuple[list[Listing], int]:
    """Filtreleme ve sayfalama ile ilanları getir"""
    query = db.query(Listing)

    # Filtreleri uygula
    if platform and platform != "all":
        query = query.filter(Listing.platform == platform)
    if kategori and kategori != "all":
        query = query.filter(Listing.kategori == kategori)
    if ilan_tipi and ilan_tipi != "all":
        query = query.filter(Listing.ilan_tipi == ilan_tipi)
    if alt_kategori and alt_kategori != "all":
        query = query.filter(Listing.alt_kategori == alt_kategori)
    if city:
        query = query.join(Location).filter(Location.il == city)
    if district:
        if not city:
            query = query.join(Location)
        query = query.filter(Location.ilce == district)
    if min_price is not None:
        query = query.filter(Listing.fiyat >= min_price)
    if max_price is not None:
        query = query.filter(Listing.fiyat <= max_price)

    # Toplam sayıyı al
    total = query.count()

    # Sayfalama
    offset = (page - 1) * limit
    listings = (
        query.options(selectinload(Listing.location))
        .order_by(Listing.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return (listings, total)


def get_listing_by_id(db: Session, listing_id: int) -> Listing | None:
    """ID ile tek bir ilan getir"""
    return db.query(Listing).filter(Listing.id == listing_id).first()


def get_listings_count(db: Session) -> int:
    """Toplam ilan sayısını getir"""
    return db.query(Listing).count()


# ============== Tarama Oturumu CRUD ==============


def create_scrape_session(
    db: Session,
    platform: str,
    kategori: str,
    ilan_tipi: str,
    alt_kategori: str | None = None,
    target_cities: list[str] | None = None,
    target_districts: dict[str, list[str]] | None = None,
) -> ScrapeSession:
    """Yeni tarama oturumu olustur."""
    session = ScrapeSession(
        platform=platform,
        kategori=kategori,
        ilan_tipi=ilan_tipi,
        alt_kategori=alt_kategori,
        target_cities=target_cities,
        target_districts=target_districts,
        status=SCRAPE_SESSION_STATUS_RUNNING,
    )
    db.add(session)
    db.flush()
    return session


def update_scrape_session(
    db: Session, session_id: int, **kwargs
) -> ScrapeSession | None:
    """Tarama oturumu alanlarını güncelle"""
    session = cast(
        Any, db.query(ScrapeSession).filter(ScrapeSession.id == session_id).first()
    )
    if not session:
        return None

    for key, value in kwargs.items():
        if hasattr(session, key):
            setattr(session, key, value)

    db.flush()
    return session


def complete_scrape_session(
    db: Session,
    session_id: int,
    status: str = SCRAPE_SESSION_STATUS_COMPLETED,
    error_message: str | None = None,
) -> ScrapeSession | None:
    """Tarama oturumunu tamamlandi olarak isaretle."""
    session = cast(
        Any, db.query(ScrapeSession).filter(ScrapeSession.id == session_id).first()
    )
    if not session:
        return None

    normalized_status = normalize_scrape_session_status(status)
    if normalized_status not in SCRAPE_SESSION_STATUS_VALUES:
        raise ValueError(f"Unsupported scrape session status: {status}")

    session.status = normalized_status
    session.completed_at = datetime.utcnow()
    if session.started_at:
        session.duration_seconds = int(
            (session.completed_at - session.started_at).total_seconds()
        )
    if error_message:
        session.error_message = error_message

    db.flush()
    return session


def normalize_legacy_scrape_session_statuses(db: Session) -> int:
    """Eski status değerlerini kanonik sete dönüştür."""
    sessions = db.query(ScrapeSession).all()
    updated = 0
    for session in sessions:
        normalized = normalize_scrape_session_status(session.status)
        if normalized != session.status:
            session.status = normalized
            updated += 1
    if updated:
        db.flush()
    return updated


def get_scrape_sessions(
    db: Session,
    platform: str | None = None,
    status: str | None = None,
    page: int = 1,
    limit: int = 50,
) -> tuple[list[ScrapeSession], int]:
    """Filtreli tarama oturumlarını getir"""
    query = db.query(ScrapeSession)

    if platform and platform != "all":
        query = query.filter(ScrapeSession.platform == platform)
    if status and status != "all":
        query = query.filter(ScrapeSession.status == status)

    total = query.count()
    offset = (page - 1) * limit
    sessions = (
        query.order_by(ScrapeSession.started_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return (sessions, total)


# ============== Analitik ==============


def get_city_analytics(
    db: Session,
    city_name: str,
    platform: str | None = None,
    kategori: str | None = None,
    ilan_tipi: str | None = None,
    alt_kategori: str | None = None,
) -> dict[str, Any]:
    """Belirli bir sehrin detayli analizlerini getir."""
    import statistics

    # Karsilastirma icin sehir adini normalize et
    def normalize_turkish(text):
        replacements = {
            "ı": "i",
            "İ": "i",
            "ş": "s",
            "Ş": "s",
            "ğ": "g",
            "Ğ": "g",
            "ü": "u",
            "Ü": "u",
            "ö": "o",
            "Ö": "o",
            "ç": "c",
            "Ç": "c",
        }
        for tr_char, ascii_char in replacements.items():
            text = text.replace(tr_char, ascii_char)
        return text.lower()

    city_normalized = normalize_turkish(city_name)

    # Eslesen lokasyonu bul
    locations = db.query(Location).all()
    matching_location_ids = []
    for loc in locations:
        if normalize_turkish(loc.il) == city_normalized:
            matching_location_ids.append(loc.id)

    if not matching_location_ids:
        return {
            "city": city_name,
            "total_listings": 0,
            "districts": [],
            "error": "Şehir bulunamadı",
            "stats": None,
            "price_ranges": [],
        }

    # İlanları sorgula
    query = db.query(Listing).filter(Listing.location_id.in_(matching_location_ids))

    if platform and platform != "all":
        query = query.filter(Listing.platform == platform)
    if kategori and kategori != "all":
        query = query.filter(Listing.kategori == kategori)
    if ilan_tipi and ilan_tipi != "all":
        query = query.filter(Listing.ilan_tipi == ilan_tipi)
    if alt_kategori and alt_kategori != "all":
        query = query.filter(Listing.alt_kategori == alt_kategori)

    listings = query.all()

    # İlçeleri al
    districts = (
        db.query(Location.ilce)
        .filter(Location.id.in_(matching_location_ids), Location.ilce.isnot(None))
        .distinct()
        .all()
    )
    district_names = sorted([d[0] for d in districts if d[0]])

    # Fiyat istatistiklerini hesapla
    prices = [
        float(listing.fiyat)
        for listing in listings
        if listing.fiyat and listing.fiyat > 0
    ]

    if not prices:
        return {
            "city": city_name,
            "total_listings": len(listings),
            "districts": district_names,
            "error": "Fiyat verisi bulunamadı",
            "stats": None,
            "price_ranges": [],
        }

    sorted_prices = sorted(prices)
    n = len(sorted_prices)

    def percentile(data: list[float], p: float) -> float:
        k = (len(data) - 1) * p / 100
        f = int(k)
        c = f + 1 if f + 1 < len(data) else f
        return data[f] + (data[c] - data[f]) * (k - f) if c < len(data) else data[f]

    stats = {
        "count": n,
        "mean": round(statistics.mean(prices), 2),
        "std": round(statistics.stdev(prices), 2) if n > 1 else 0,
        "min": round(min(prices), 2),
        "q25": round(percentile(sorted_prices, 25), 2),
        "median": round(statistics.median(prices), 2),
        "q75": round(percentile(sorted_prices, 75), 2),
        "max": round(max(prices), 2),
    }

    # Fiyat araligi dagilimi
    num_bins = 5
    bin_edges = [
        percentile(sorted_prices, i * 100 / num_bins) for i in range(num_bins + 1)
    ]

    unique_edges: list[float] = []
    for e in bin_edges:
        if not unique_edges or e > unique_edges[-1]:
            unique_edges.append(e)

    if len(unique_edges) < 3:
        min_p, max_p = min(prices), max(prices)
        bin_width = (max_p - min_p) / num_bins
        unique_edges = [min_p + i * bin_width for i in range(num_bins + 1)]

    def format_price(p: float) -> str:
        if p >= 1000000:
            return f"{p / 1000000:.1f}M"
        elif p >= 1000:
            return f"{p / 1000:.0f}K"
        else:
            return f"{p:.0f}"

    price_ranges: list[dict[str, Any]] = []
    for i in range(len(unique_edges) - 1):
        low = unique_edges[i]
        high = unique_edges[i + 1]
        label = f"{format_price(low)} - {format_price(high)}"

        if i == len(unique_edges) - 2:
            count = sum(1 for p in prices if low <= p <= high)
        else:
            count = sum(1 for p in prices if low <= p < high)

        price_ranges.append(
            {"range": label, "count": count, "percentage": round(count / n * 100, 1)}
        )

    return {
        "city": city_name,
        "total_listings": len(listings),
        "districts": district_names,
        "stats": stats,
        "price_ranges": price_ranges,
    }


def get_last_scrape(db: Session) -> str:
    latest_listing = select(func.max(Listing.created_at).label("created_at")).subquery()
    latest_session = (
        select(ScrapeSession.started_at, ScrapeSession.completed_at)
        .order_by(ScrapeSession.started_at.desc())
        .limit(1)
        .subquery()
    )
    dates = db.execute(
        select(
            latest_listing.c.created_at,
            latest_session.c.started_at,
            latest_session.c.completed_at,
        ).select_from(latest_listing.outerjoin(latest_session, true()))
    ).one()
    return format_istanbul(latest_datetime(*dates))


def get_stats_summary(db: Session) -> dict[str, Any]:
    """Kontrol paneli için genel istatistikleri getir"""
    from datetime import timedelta

    now = now_utc_naive()
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    total_listings = db.query(Listing).count()
    total_sessions = db.query(ScrapeSession).count()

    this_week = (
        db.query(ScrapeSession).filter(ScrapeSession.started_at >= week_ago).count()
    )
    this_month = (
        db.query(ScrapeSession).filter(ScrapeSession.started_at >= month_ago).count()
    )

    return {
        "total_scrapes": total_sessions,
        "total_listings": total_listings,
        "this_week": this_week,
        "this_month": this_month,
        "last_scrape": get_last_scrape(db),
    }


# ============== Basarisiz Sayfa CRUD ==============


def create_failed_page(
    db: Session,
    scrape_session_id: int,
    url: str,
    page_number: int | None = None,
    city: str | None = None,
    district: str | None = None,
    error_message: str | None = None,
) -> FailedPage:
    """Basarisiz sayfayi kaydet."""
    failed = FailedPage(
        scrape_session_id=scrape_session_id,
        url=url,
        page_number=page_number,
        city=city,
        district=district,
        error_message=error_message,
    )
    db.add(failed)
    db.flush()
    return failed
