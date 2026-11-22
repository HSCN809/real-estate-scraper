"""Read models for grouped results and price charts."""

import hashlib
import json
import re
from collections import Counter, defaultdict
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy import and_, case, func, select
from sqlalchemy.orm import Session
from utils.timezone import format_istanbul, to_iso, to_istanbul

from .models import Listing, Location

_PLATFORM = {"hepsiemlak": "HepsiEmlak", "emlakjet": "Emlakjet"}
_CATEGORY = {
    "konut": "Konut",
    "arsa": "Arsa",
    "isyeri": "İşyeri",
    "devremulk": "Devremülk",
    "turistik_isletme": "Turistik İşletme",
    "turistik_tesis": "Turistik Tesis",
}
_LISTING_TYPE = {"satilik": "Satılık", "kiralik": "Kiralık"}
_UNKNOWN = "Bilinmiyor"
_UNKNOWN_LOCATION = {
    "",
    "belirtilmemis",
    "bilinmiyor",
    "unknown",
    "none",
    "null",
    "yok",
}
_TURKISH_ASCII = str.maketrans("ıİşŞğĞüÜöÖçÇ", "iissgguuoocc")
_GROUP = (
    Location.il,
    Location.ilce,
    Listing.platform,
    Listing.kategori,
    Listing.ilan_tipi,
    Listing.alt_kategori,
)


class ResultsFilters(BaseModel):
    platform: str | None = Field(default=None, max_length=50)
    category: str | None = Field(default=None, max_length=100)
    listing_type: str | None = Field(default=None, max_length=50)
    subtype: str | None = Field(default=None, max_length=100)
    city: list[str] = Field(default_factory=list, max_length=100)
    district: list[str] = Field(default_factory=list, max_length=1000)


class ResultsPageQuery(ResultsFilters):
    page: int = Field(default=1, ge=1, le=1_000_000_000)
    limit: int = Field(default=20, ge=1, le=100)


def _location_name(value: str | None) -> str | None:
    text = (value or "").strip()
    compact = re.sub(r"[\s\-_]+", "", text.translate(_TURKISH_ASCII).casefold())
    return text if compact not in _UNKNOWN_LOCATION else None


def _code(value: str, labels: dict[str, str]) -> str:
    normalized = value.strip().casefold()
    return next(
        (key for key, label in labels.items() if label.casefold() == normalized),
        normalized,
    )


def _conditions(db: Session, filters: ResultsFilters):
    conditions = []
    for column, value, labels in (
        (Listing.platform, filters.platform, _PLATFORM),
        (Listing.kategori, filters.category, _CATEGORY),
        (Listing.ilan_tipi, filters.listing_type, _LISTING_TYPE),
    ):
        if value and value != "all":
            conditions.append(column == _code(value, labels))
    if filters.subtype and filters.subtype != "all":
        subtype = re.sub(r"[\s\-]+", "_", filters.subtype.strip().casefold())
        conditions.append(Listing.alt_kategori == subtype)
    for column, values, missing in (
        (Location.il, filters.city, _UNKNOWN),
        (Location.ilce, filters.district, ""),
    ):
        if values:
            selected = set(values)
            raw_values = [
                name
                for name in db.scalars(select(column).distinct())
                if (_location_name(name) or missing) in selected
            ]
            conditions.append(column.in_(raw_values))
    return conditions


def _groups(conditions=()):
    return (
        select(
            *_GROUP,
            func.count(Listing.id).label("count"),
            func.max(Listing.created_at).label("last_date"),
        )
        .join_from(Listing, Location)
        .where(*conditions)
        .group_by(*_GROUP)
    )


def _result_item(row) -> dict[str, Any]:
    keys = [
        row.il,
        row.ilce,
        row.platform,
        row.kategori,
        row.ilan_tipi,
        row.alt_kategori,
    ]
    result_id = hashlib.sha256(json.dumps(keys).encode()).hexdigest()
    return {
        "id": f"db_{result_id}",
        "platform": _PLATFORM.get(row.platform, row.platform),
        "category": _CATEGORY.get(row.kategori, row.kategori),
        "subtype": row.alt_kategori.replace("_", " ").title()
        if row.alt_kategori
        else None,
        "listing_type": _LISTING_TYPE.get(row.ilan_tipi, row.ilan_tipi),
        "city": _location_name(row.il) or _UNKNOWN,
        "district": _location_name(row.ilce),
        "date": format_istanbul(row.last_date),
        "date_iso": to_iso(row.last_date),
        "count": row.count,
        "avg_price": round(row.avg_price, 2) if row.avg_price is not None else None,
        "file_size": 0,
        "file_size_mb": 0,
        "status": "completed",
        "files": [],
    }


def get_results_page(db: Session, filters: ResultsPageQuery) -> dict[str, Any]:
    groups = _groups(_conditions(db, filters))
    page = filters.page
    query = groups.add_columns(
        func.avg(Listing.fiyat).label("avg_price"),
        func.count().over().label("total"),
    ).order_by(func.max(Listing.created_at).desc().nulls_last(), *_GROUP)
    page_rows = db.execute(
        query.offset((page - 1) * filters.limit).limit(filters.limit)
    ).all()
    total = page_rows[0].total if page_rows else 0
    if not page_rows and page > 1:
        # Recover the last valid page when filtering or deletion shrinks the result set.
        total = db.scalar(select(func.count()).select_from(groups.subquery())) or 0
        page = max(1, (total + filters.limit - 1) // filters.limit)
        if total:
            page_rows = db.execute(
                query.offset((page - 1) * filters.limit).limit(filters.limit)
            ).all()
    return {
        "items": [_result_item(row) for row in page_rows],
        "page": page,
        "limit": filters.limit,
        "pages": (total + filters.limit - 1) // filters.limit,
        "total": total,
    }


def get_results_filters(db: Session) -> dict[str, Any]:
    locations: dict[str, set[str]] = defaultdict(set)
    platforms, categories, listing_types, subtypes = set(), set(), set(), set()
    total_groups = total_listings = 0
    for row in db.execute(_groups()):
        total_groups += 1
        total_listings += row.count
        districts = locations[_location_name(row.il) or _UNKNOWN]
        district = _location_name(row.ilce)
        if district:
            districts.add(district)
        platforms.add(_PLATFORM.get(row.platform, row.platform))
        categories.add(_CATEGORY.get(row.kategori, row.kategori))
        listing_types.add(_LISTING_TYPE.get(row.ilan_tipi, row.ilan_tipi))
        if row.alt_kategori:
            subtypes.add(row.alt_kategori.replace("_", " ").title())
    return {
        "platforms": sorted(platforms),
        "categories": sorted(categories),
        "listing_types": sorted(listing_types),
        "subtypes": sorted(subtypes),
        "locations": {city: sorted(districts) for city, districts in locations.items()},
        "total_groups": total_groups,
        "total_listings": total_listings,
    }


def get_results_overview(db: Session, filters: ResultsFilters) -> dict[str, Any]:
    cities: Counter[str] = Counter()
    platforms: Counter[str] = Counter()
    categories: Counter[str] = Counter()
    listing_types: Counter[str] = Counter()
    history: Counter[str] = Counter()
    for row in db.execute(_groups(_conditions(db, filters))):
        cities[_location_name(row.il) or _UNKNOWN] += row.count
        platforms[_PLATFORM.get(row.platform, row.platform)] += row.count
        categories[_CATEGORY.get(row.kategori, row.kategori)] += row.count
        listing_types[_LISTING_TYPE.get(row.ilan_tipi, row.ilan_tipi)] += row.count
        if row.last_date:
            local_day = to_istanbul(row.last_date).date().isoformat()
            history[local_day] += row.count
    return {
        "cities": [
            {"city": name, "count": count} for name, count in cities.most_common()
        ],
        "platforms": dict(platforms),
        "categories": dict(categories),
        "listing_types": dict(listing_types),
        "history": [
            {"date": date, "count": history[date]} for date in sorted(history)[-10:]
        ],
    }


def _price_histogram(db: Session, prices, count: int) -> list[dict[str, Any]]:
    # Preserve the chart's decile edges. The database returns only the selected ranks.
    ranks = {1, count, *(count * i // 10 + 1 for i in range(1, 10))}
    ranked = select(
        prices.c.price, func.row_number().over(order_by=prices.c.price).label("rank")
    ).subquery()
    edges = sorted(
        set(db.scalars(select(ranked.c.price).where(ranked.c.rank.in_(ranks))))
    )
    if len(edges) == 1:
        return [{"min": edges[0], "max": edges[0], "count": count}]

    intervals = list(zip(edges, edges[1:]))
    buckets = []
    for i, (low, high) in enumerate(intervals):
        upper = (
            prices.c.price <= high if i == len(intervals) - 1 else prices.c.price < high
        )
        buckets.append(func.sum(case((and_(prices.c.price >= low, upper), 1), else_=0)))
    bucket_counts = db.execute(select(*buckets).select_from(prices)).one()
    return [
        {"min": low, "max": high, "count": bucket_count}
        for (low, high), bucket_count in zip(intervals, bucket_counts)
    ]


def get_price_summary(db: Session, filters: ResultsFilters) -> dict[str, Any]:
    prices = (
        select(
            Listing.fiyat.label("price"),
            func.trim(Location.il).label("city"),
            Listing.platform,
        )
        .join_from(Listing, Location)
        .where(Listing.fiyat > 0, *_conditions(db, filters))
        .subquery()
    )
    price = prices.c.price
    avg = func.avg(price)
    count, average, minimum, maximum = db.execute(
        select(func.count(price), avg, func.min(price), func.max(price))
    ).one()
    cities, platforms, histogram = [], [], []
    if count:
        cities = [
            {"city": _location_name(city) or _UNKNOWN, "avg_price": round(value, 2)}
            for city, value in db.execute(
                select(prices.c.city, avg)
                .group_by(prices.c.city)
                .order_by(avg.desc(), prices.c.city)
                .limit(10)
            )
        ]
        platforms = [
            {
                "platform": _PLATFORM.get(platform, platform),
                "avg_price": round(value, 2),
            }
            for platform, value in db.execute(
                select(prices.c.platform, avg)
                .group_by(prices.c.platform)
                .order_by(prices.c.platform)
            )
        ]
        histogram = _price_histogram(db, prices, count)
    return {
        "summary": {
            "total_count": count,
            "avg_price": round(average, 2) if average is not None else 0,
            "min_price": minimum if minimum is not None else 0,
            "max_price": maximum if maximum is not None else 0,
        },
        "cities": cities,
        "platforms": platforms,
        "histogram": histogram,
    }
