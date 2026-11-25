"""Read models for grouped results and price charts."""

import hashlib
import json
import re
from collections import Counter, OrderedDict, defaultdict
from threading import Lock
from time import monotonic
from typing import Any, Callable, TypeVar
from weakref import WeakKeyDictionary

from pydantic import BaseModel, Field
from sqlalchemy import and_, case, func, or_, select, true
from sqlalchemy.orm import Session
from utils.timezone import format_istanbul, to_iso, to_istanbul

from .models import Listing, Location

T = TypeVar("T")
_READ_CACHE_TTL_SECONDS = 15.0
_READ_CACHE_MAX_ENTRIES = 256
_read_cache: OrderedDict[tuple[Any, ...], tuple[float, Any]] = OrderedDict()
_bind_ids: WeakKeyDictionary[Any, int] = WeakKeyDictionary()
_cache_lock = Lock()
_cache_epoch = 0
_next_bind_seq = 0


def invalidate_results_cache() -> None:
    """Clear in-process read-model cache after listing mutations."""
    global _cache_epoch
    with _cache_lock:
        _cache_epoch += 1
        _read_cache.clear()


def _bind_token(db: Session) -> int:
    global _next_bind_seq
    bind = db.get_bind()
    bind = getattr(bind, "engine", bind)
    token = _bind_ids.get(bind)
    if token is None:
        _next_bind_seq += 1
        token = _next_bind_seq
        _bind_ids[bind] = token
    return token


def cached_read(
    db: Session,
    namespace: str,
    key: Any,
    loader: Callable[[], T],
    ttl: float = _READ_CACHE_TTL_SECONDS,
) -> T:
    """Return a short-lived TTL-cached read result scoped to the active engine and write epoch."""
    with _cache_lock:
        cache_key = (_bind_token(db), _cache_epoch, namespace, key)
        entry = _read_cache.get(cache_key)
        now = monotonic()
        if entry is not None:
            expires_at, value = entry
            if now < expires_at:
                _read_cache.move_to_end(cache_key)
                return value
            del _read_cache[cache_key]
        epoch_before = _cache_epoch

    value = loader()

    with _cache_lock:
        if _cache_epoch == epoch_before:
            _read_cache[cache_key] = (monotonic() + ttl, value)
            _read_cache.move_to_end(cache_key)
            while len(_read_cache) > _READ_CACHE_MAX_ENTRIES:
                _read_cache.popitem(last=False)
    return value

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


def _location_values_map(
    db: Session, cache_name: str, column: Any, missing: str
) -> dict[str, tuple[str, ...]]:
    def _build() -> dict[str, tuple[str, ...]]:
        grouped: dict[str, list[str]] = defaultdict(list)
        for name in db.scalars(select(column).distinct()):
            grouped[_location_name(name) or missing].append(name)
        return {key: tuple(values) for key, values in grouped.items()}

    return cached_read(db, "_location_map", cache_name, _build)


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
    for cache_name, column, values, missing in (
        ("city", Location.il, filters.city, _UNKNOWN),
        ("district", Location.ilce, filters.district, ""),
    ):
        if values:
            mapping = _location_values_map(db, cache_name, column, missing)
            raw_values = [
                raw
                for canonical in dict.fromkeys(values)
                for raw in mapping.get(canonical, ())
            ]
            conditions.append(column.in_(raw_values))
    return conditions


def _groups(conditions=(), *, include_avg_price: bool = False):
    cols = [
        *_GROUP,
        func.count(Listing.id).label("count"),
        *(
            [func.avg(Listing.fiyat).label("avg_price")]
            if include_avg_price
            else []
        ),
        func.max(Listing.created_at).label("last_date"),
    ]
    return (
        select(*cols)
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


def _result_order(grouped_rows):
    return (
        grouped_rows.c.last_date.desc().nulls_last(),
        *(grouped_rows.c[column.key] for column in _GROUP),
    )


def get_results_page(db: Session, filters: ResultsPageQuery) -> dict[str, Any]:
    groups = _groups(
        _conditions(db, filters), include_avg_price=True
    ).cte("result_groups")
    # Count and page read the same grouped snapshot without re-joining base tables.
    count = func.count()
    last_page = (count + filters.limit - 1) // filters.limit
    pagination = (
        select(
            count.label("total"),
            case(
                (count == 0, 1),
                (last_page < filters.page, last_page),
                else_=filters.page,
            ).label("page"),
        )
        .select_from(groups)
        .cte("result_pagination")
    )
    offset = select((pagination.c.page - 1) * filters.limit).scalar_subquery()
    page_rows = (
        select(groups)
        .order_by(*_result_order(groups))
        .offset(offset)
        .limit(filters.limit)
        .subquery("result_page")
    )
    rows = db.execute(
        select(pagination, page_rows)
        .select_from(pagination.outerjoin(page_rows, true()))
        .order_by(*_result_order(page_rows))
    ).all()
    total = rows[0].total
    return {
        "items": [_result_item(row) for row in rows if row.platform is not None],
        "page": rows[0].page,
        "limit": filters.limit,
        "pages": (total + filters.limit - 1) // filters.limit,
        "total": total,
    }


class _Overview:
    def __init__(self) -> None:
        self.cities: Counter[str] = Counter()
        self.platforms: Counter[str] = Counter()
        self.categories: Counter[str] = Counter()
        self.listing_types: Counter[str] = Counter()
        self.history: Counter[str] = Counter()

    def add(self, row, city: str) -> None:
        self.cities[city] += row.count
        self.platforms[_PLATFORM.get(row.platform, row.platform)] += row.count
        self.categories[_CATEGORY.get(row.kategori, row.kategori)] += row.count
        self.listing_types[_LISTING_TYPE.get(row.ilan_tipi, row.ilan_tipi)] += row.count
        if row.last_date:
            local_day = to_istanbul(row.last_date).date().isoformat()
            self.history[local_day] += row.count

    def to_dict(self) -> dict[str, Any]:
        return {
            "cities": [
                {"city": name, "count": count}
                for name, count in self.cities.most_common()
            ],
            "platforms": dict(self.platforms),
            "categories": dict(self.categories),
            "listing_types": dict(self.listing_types),
            "history": [
                {"date": day, "count": self.history[day]}
                for day in sorted(self.history)[-10:]
            ],
        }


def get_results_filters(
    db: Session, *, include_overview: bool = False
) -> dict[str, Any]:
    locations: dict[str, set[str]] = defaultdict(set)
    platforms, categories, listing_types, subtypes = set(), set(), set(), set()
    total_groups = total_listings = 0
    overview = _Overview() if include_overview else None
    for row in db.execute(_groups()):
        total_groups += 1
        total_listings += row.count
        city = _location_name(row.il) or _UNKNOWN
        districts = locations[city]
        district = _location_name(row.ilce)
        if district:
            districts.add(district)
        platforms.add(_PLATFORM.get(row.platform, row.platform))
        categories.add(_CATEGORY.get(row.kategori, row.kategori))
        listing_types.add(_LISTING_TYPE.get(row.ilan_tipi, row.ilan_tipi))
        if row.alt_kategori:
            subtypes.add(row.alt_kategori.replace("_", " ").title())
        if overview is not None:
            overview.add(row, city)
    metadata = {
        "platforms": sorted(platforms),
        "categories": sorted(categories),
        "listing_types": sorted(listing_types),
        "subtypes": sorted(subtypes),
        "locations": {city: sorted(districts) for city, districts in locations.items()},
        "total_groups": total_groups,
        "total_listings": total_listings,
    }
    if overview is not None:
        metadata["overview"] = overview.to_dict()
    return metadata


def get_results_overview(db: Session, filters: ResultsFilters) -> dict[str, Any]:
    overview = _Overview()
    for row in db.execute(_groups(_conditions(db, filters))):
        overview.add(row, _location_name(row.il) or _UNKNOWN)
    return overview.to_dict()


def _price_histogram(
    db: Session, prices, count: int, minimum: float, maximum: float
) -> list[dict[str, Any]]:
    if minimum == maximum:
        return [{"min": minimum, "max": maximum, "count": count}]

    # Preserve the chart's decile edges and bucket counts in one CTE pass over filtered prices.
    ranks = {1, count, *(count * i // 10 + 1 for i in range(1, 10))}
    ranked = select(
        prices.c.price.label("price"),
        func.row_number().over(order_by=prices.c.price).label("rn"),
    ).cte("ranked_prices")
    edge_vals = (
        select(ranked.c.price.label("edge"))
        .where(ranked.c.rn.in_(ranks))
        .distinct()
        .cte("price_edges")
    )
    bounds = select(
        edge_vals.c.edge.label("low"),
        func.lead(edge_vals.c.edge).over(order_by=edge_vals.c.edge).label("high"),
        func.lead(edge_vals.c.edge, 2).over(order_by=edge_vals.c.edge).label("next_high"),
    ).cte("price_bounds")
    bucket_rows = db.execute(
        select(bounds.c.low, bounds.c.high, func.count(ranked.c.price))
        .select_from(
            bounds.outerjoin(
                ranked,
                and_(
                    ranked.c.price >= bounds.c.low,
                    or_(
                        ranked.c.price < bounds.c.high,
                        and_(
                            bounds.c.next_high.is_(None),
                            ranked.c.price <= bounds.c.high,
                        ),
                    ),
                ),
            )
        )
        .where(bounds.c.high.isnot(None))
        .group_by(bounds.c.low, bounds.c.high, bounds.c.next_high)
        .order_by(bounds.c.low)
    ).all()
    return [
        {"min": low, "max": high, "count": bucket_count}
        for low, high, bucket_count in bucket_rows
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
    platform_rows = db.execute(
        select(
            prices.c.platform,
            func.count(price),
            func.sum(price),
            func.min(price),
            func.max(price),
        )
        .group_by(prices.c.platform)
        .order_by(prices.c.platform)
    ).all()
    count = sum(row[1] for row in platform_rows)
    cities, platforms, histogram = [], [], []
    average = minimum = maximum = None
    if count:
        total_sum = sum(row[2] for row in platform_rows)
        average = total_sum / count
        minimum = min(row[3] for row in platform_rows)
        maximum = max(row[4] for row in platform_rows)
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
                "avg_price": round(platform_sum / platform_count, 2),
            }
            for platform, platform_count, platform_sum, _pmin, _pmax in platform_rows
        ]
        histogram = _price_histogram(db, prices, count, minimum, maximum)
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
