import re
import unicodedata
from urllib.parse import urlparse

from core.config import get_emlakjet_config


def normalize_slug(value: str | None) -> str:
    text = str(value or "").strip().lower().replace("_", "-")
    normalized = unicodedata.normalize("NFKD", text)
    ascii_only = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    ascii_only = (
        ascii_only.replace("ı", "i")
        .replace("ş", "s")
        .replace("ğ", "g")
        .replace("ü", "u")
        .replace("ö", "o")
        .replace("ç", "c")
    )
    ascii_only = re.sub(r"[^a-z0-9-]+", "-", ascii_only)
    return re.sub(r"-{2,}", "-", ascii_only).strip("-")


def extract_primary_slug_from_url(listing_url: str) -> str | None:
    if not listing_url:
        return None

    try:
        parsed = urlparse(listing_url)
        host = (parsed.netloc or "").lower()
        if host and "emlakjet.com" not in host:
            return None

        parts = [normalize_slug(part) for part in parsed.path.split("/") if part]
        if not parts:
            return None

        for part in parts:
            if re.match(r"^(satilik|kiralik)-[a-z0-9-]+$", part):
                return part

        path_slug = normalize_slug(parsed.path)
        embedded_match = re.search(r"(satilik|kiralik)-[a-z0-9-]+", path_slug)
        if embedded_match:
            return embedded_match.group(0)

        if parts[0] == "ilan":
            return "ilan"

        return parts[0]
    except Exception:
        return None


def get_expected_primary_slugs(listing_type: str, category: str) -> set[str]:
    expected: set[str] = set()
    cfg = get_emlakjet_config()
    category_map = cfg.categories.get(listing_type or "", {})
    category_path = str(category_map.get(category or "", "")).strip("/")
    if category_path:
        expected.add(normalize_slug(category_path.split("/")[0]))

    try:
        from .subtype_fetcher import fetch_subtypes

        for subtype in fetch_subtypes(listing_type, category):
            subtype_path = str(subtype.get("path", "")).strip("/")
            subtype_id = normalize_slug(str(subtype.get("id", "")))
            if subtype_path:
                expected.add(normalize_slug(subtype_path.split("/")[0]))
            if subtype_id:
                expected.add(subtype_id)
                listing_prefix = normalize_slug(listing_type)
                if listing_prefix:
                    expected.add(f"{listing_prefix}-{subtype_id}")
    except Exception:  # nosec
        pass

    return {slug for slug in expected if slug}


def get_disallowed_primary_slugs(listing_type: str, category: str) -> set[str]:
    disallowed: set[str] = set()
    cfg = get_emlakjet_config()
    category_map = cfg.categories.get(listing_type or "", {})
    for cat_key, cat_path in category_map.items():
        if cat_key == category:
            continue
        path = str(cat_path or "").strip("/")
        if path:
            disallowed.add(normalize_slug(path.split("/")[0]))
    return disallowed


def matches_filters(
    listing_url: str,
    listing_type: str,
    category: str,
    alt_kategori: str | None,
    expected_primary_slugs: set[str],
    disallowed_primary_slugs: set[str],
) -> bool:
    extracted = extract_primary_slug_from_url(listing_url)
    if extracted is None:
        return False
    if extracted == "ilan":
        return True

    selected_subtype = normalize_slug(alt_kategori)
    if selected_subtype:
        return extracted == selected_subtype or extracted.endswith(
            f"-{selected_subtype}"
        )

    if expected_primary_slugs and extracted in expected_primary_slugs:
        return True

    listing_prefix = normalize_slug(listing_type)
    category_slug = normalize_slug(category)

    if (
        category_slug == "konut"
        and listing_prefix
        and extracted.startswith(f"{listing_prefix}-")
    ):
        return extracted not in disallowed_primary_slugs

    if category_slug and category_slug in extracted:
        return True

    if disallowed_primary_slugs and extracted in disallowed_primary_slugs:
        return False

    return not expected_primary_slugs
