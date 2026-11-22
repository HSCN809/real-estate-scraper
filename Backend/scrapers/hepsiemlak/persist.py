from utils.logger import get_logger

from .filters import get_expected_subtype_slugs, matches_filters

logger = get_logger(__name__)


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

        if platform == "hepsiemlak":
            expected_subtypes = get_expected_subtype_slugs(ilan_tipi, kategori)
            filtered_records: list[dict] = []
            filtered_out = 0

            for data in listings:
                listing_url = data.get("ilan_linki") or data.get("ilan_url")
                if matches_filters(
                    listing_url=str(listing_url or ""),
                    listing_type=ilan_tipi,
                    category=kategori,
                    alt_kategori=alt_kategori,
                    expected_subtypes=expected_subtypes,
                ):
                    filtered_records.append(data)
                else:
                    filtered_out += 1

            if filtered_out > 0:
                logger.warning(
                    "Filtered %s listings due to mismatched listing_type/category/subtype "
                    "(listing_type=%s, kategori=%s, alt_kategori=%s)",
                    filtered_out,
                    ilan_tipi,
                    kategori,
                    alt_kategori,
                )

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
                f"DB save: {new_count} new, {updated_count} updated, {unchanged_count} unchanged"
            )
        return new_count, updated_count, unchanged_count
    except Exception as e:
        logger.error(f"DB save error: {e}")
        db.rollback()
        return 0, 0, 0
