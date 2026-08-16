from datetime import UTC, datetime

from utils.timezone import format_istanbul, latest_datetime, to_iso, to_istanbul


def test_naive_utc_converts_to_istanbul():
    dt = datetime(2026, 8, 16, 13, 0, 0)  # noqa: DTZ001
    istanbul = to_istanbul(dt)
    assert istanbul.hour == 16
    assert istanbul.tzinfo is not None
    assert format_istanbul(dt) == "16.08.2026 16:00"


def test_aware_utc_converts_to_istanbul():
    dt = datetime(2026, 8, 16, 13, 0, 0, tzinfo=UTC)
    assert format_istanbul(dt) == "16.08.2026 16:00"


def test_to_iso_marks_naive_as_utc():
    dt = datetime(2026, 8, 16, 13, 0, 0)  # noqa: DTZ001
    assert to_iso(dt) == "2026-08-16T13:00:00+00:00"


def test_format_istanbul_none():
    assert format_istanbul(None) == "-"


def test_latest_datetime_prefers_newer_session_over_old_listing():
    listing_at = datetime(2026, 8, 12, 20, 1, 0, tzinfo=UTC)
    session_at = datetime(2026, 8, 16, 13, 30, 0, tzinfo=UTC)
    latest = latest_datetime(listing_at, session_at)
    assert latest == session_at
    assert format_istanbul(latest) == "16.08.2026 16:30"
