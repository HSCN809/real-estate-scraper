from datetime import UTC, datetime
from zoneinfo import ZoneInfo

ISTANBUL = ZoneInfo("Europe/Istanbul")


def to_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def to_istanbul(dt: datetime) -> datetime:
    return to_utc(dt).astimezone(ISTANBUL)


def format_istanbul(dt: datetime | None) -> str:
    if dt is None:
        return "-"
    return to_istanbul(dt).strftime("%d.%m.%Y %H:%M")


def to_iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return to_utc(dt).isoformat()


def now_istanbul() -> datetime:
    return datetime.now(ISTANBUL)


def now_utc_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def latest_datetime(*values: datetime | None) -> datetime | None:
    present = [value for value in values if value is not None]
    return max(present) if present else None
