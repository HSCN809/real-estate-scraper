from urllib.parse import urlparse


def extract_subtype_slug_from_url(listing_url: str, listing_type: str) -> str | None:
    if not listing_url:
        return None

    try:
        parsed = urlparse(listing_url)
        host = (parsed.netloc or "").lower()
        if host and "hepsiemlak.com" not in host:
            return None

        parts = [part for part in parsed.path.split("/") if part]
        if not parts:
            return None

        listing_type_marker = f"-{listing_type.lower()}"
        first_segment = parts[0].lower()
        if (
            listing_type_marker not in first_segment
            and first_segment != listing_type.lower()
        ):
            return None

        if len(parts) < 2:
            return ""

        return parts[1].strip().lower()
    except Exception:
        return None


def get_expected_subtype_slugs(listing_type: str, category: str) -> set[str]:
    expected_slugs: set[str] = set()
    if not listing_type or not category:
        return expected_slugs

    try:
        from .subtype_fetcher import fetch_subtypes

        for subtype in fetch_subtypes(listing_type, category):
            subtype_id = str(subtype.get("id", "")).strip().lower().replace("_", "-")
            subtype_path = str(subtype.get("path", "")).strip().lower()
            if subtype_id:
                expected_slugs.add(subtype_id)
            if subtype_path:
                path_parts = [
                    part for part in subtype_path.strip("/").split("/") if part
                ]
                if len(path_parts) >= 2:
                    expected_slugs.add(path_parts[-1])
    except Exception:  # nosec
        pass

    if expected_slugs:
        expected_slugs.add(category.replace("_", "-").lower())

    return expected_slugs


def matches_filters(
    listing_url: str,
    listing_type: str,
    category: str,
    alt_kategori: str | None,
    expected_subtypes: set[str],
) -> bool:
    extracted_slug = extract_subtype_slug_from_url(listing_url, listing_type)
    if extracted_slug is None:
        return False

    selected_subtype = (alt_kategori or "").replace("_", "-").strip().lower()
    if selected_subtype:
        return extracted_slug == selected_subtype

    if category == "konut" and (not extracted_slug or extracted_slug[0].isdigit()):
        return True

    if not expected_subtypes:
        return True

    return extracted_slug in expected_subtypes
