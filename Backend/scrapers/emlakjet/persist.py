from utils.logger import get_logger

from .filters import (
    get_disallowed_primary_slugs,
    get_expected_primary_slugs,
    matches_filters,
)

logger = get_logger(__name__)
_URL_FILTER_FALLBACK_LOGGED: set[tuple] = set()


def save_listings_to_db(
    db,
    listings: list[dict],
    platform: str,
    kategori: str,
    ilan_tipi: str,
    alt_kategori: str | None = None,
    scrape_session_id: int | None = None,
    log_db_save: bool = True,
):
    if not db:
        return 0, 0, 0

    try:
        from database import crud

        records_to_save = listings

        if platform == "emlakjet":
            expected_primary_slugs = get_expected_primary_slugs(ilan_tipi, kategori)
            disallowed_primary_slugs = get_disallowed_primary_slugs(ilan_tipi, kategori)
            filtered_records: list[dict] = []
            filtered_out = 0

            for data in listings:
                listing_url = data.get("ilan_url") or data.get("ilan_linki")
                if matches_filters(
                    listing_url=str(listing_url or ""),
                    listing_type=ilan_tipi,
                    category=kategori,
                    alt_kategori=alt_kategori,
                    expected_primary_slugs=expected_primary_slugs,
                    disallowed_primary_slugs=disallowed_primary_slugs,
                ):
                    filtered_records.append(data)
                else:
                    filtered_out += 1

            if filtered_out > 0 and filtered_records:
                logger.info(
                    "URL filter skipped %s/%s listings (kept=%s) "
                    "(listing_type=%s, kategori=%s, alt_kategori=%s)",
                    filtered_out,
                    len(listings),
                    len(filtered_records),
                    ilan_tipi,
                    kategori,
                    alt_kategori,
                )

            if listings and not filtered_records:
                fallback_log_key = (
                    scrape_session_id,
                    ilan_tipi,
                    kategori,
                    alt_kategori,
                )
                if fallback_log_key not in _URL_FILTER_FALLBACK_LOGGED:
                    logger.info(
                        "URL filter matched none; using unfiltered fallback save "
                        "(listings=%s, listing_type=%s, kategori=%s, alt_kategori=%s)",
                        len(listings),
                        ilan_tipi,
                        kategori,
                        alt_kategori,
                    )
                    _URL_FILTER_FALLBACK_LOGGED.add(fallback_log_key)
                records_to_save = listings
            else:
                records_to_save = filtered_records

        new_count, updated_count, unchanged_count = crud.upsert_listings(
            db,
            records_to_save,
            platform=platform,
            kategori=kategori,
            ilan_tipi=ilan_tipi,
            alt_kategori=alt_kategori,
            scrape_session_id=scrape_session_id,
        )

        db.commit()
        if log_db_save:
            logger.info(
                "DB save: %s new, %s updated, %s unchanged",
                new_count,
                updated_count,
                unchanged_count,
            )
        return new_count, updated_count, unchanged_count
    except Exception as exc:
        logger.error(f"DB save error: {exc}")
        db.rollback()
        return 0, 0, 0
