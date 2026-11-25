"""HepsiEmlak alt kategori çekici ve önbellek yöneticisi - Selenium ile bir kez çeker, JSON'a kaydeder, sonra hep dosyadan okur"""

import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from core.config import get_hepsiemlak_config
from utils.logger import get_logger

logger = get_logger(__name__)

# JSON dosya yolu
SUBCATEGORIES_JSON_PATH = Path(__file__).parent / "subcategories.json"
_SUBCATEGORIES_CACHE: tuple[tuple[str, int], dict[str, dict[str, list[dict]]]] | None = None


def load_subcategories_from_json() -> dict[str, dict[str, list[dict]]]:
    """JSON dosyasından subcategories yükle (mtime tabanlı bellek önbellekli)."""
    global _SUBCATEGORIES_CACHE
    if SUBCATEGORIES_JSON_PATH.exists():
        try:
            cache_key = (
                str(SUBCATEGORIES_JSON_PATH),
                SUBCATEGORIES_JSON_PATH.stat().st_mtime_ns,
            )
            if _SUBCATEGORIES_CACHE is not None and _SUBCATEGORIES_CACHE[0] == cache_key:
                return _SUBCATEGORIES_CACHE[1]
            with open(SUBCATEGORIES_JSON_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            _SUBCATEGORIES_CACHE = (cache_key, data)
            return data
        except Exception as e:
            logger.error(f"JSON okuma hatası: {e}")
    return {}


def save_subcategories_to_json(data: dict[str, dict[str, list[dict]]]):
    """Subcategories'i JSON dosyasına kaydet"""
    global _SUBCATEGORIES_CACHE
    try:
        with open(SUBCATEGORIES_JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        _SUBCATEGORIES_CACHE = None
        logger.info(f"Subcategories kaydedildi: {SUBCATEGORIES_JSON_PATH}")
    except Exception as e:
        logger.error(f"JSON yazma hatası: {e}")


def merge_subcategories(
    new_data: dict[str, dict[str, list[dict]]],
    old_data: dict[str, dict[str, list[dict]]],
) -> dict[str, dict[str, list[dict]]]:
    merged = {lt: dict(cats) for lt, cats in new_data.items()}
    for listing_type, categories in old_data.items():
        merged.setdefault(listing_type, {})
        for category, subtypes in categories.items():
            if not merged[listing_type].get(category) and subtypes:
                merged[listing_type][category] = subtypes
    return merged


def parse_hepsiemlak_subtype_links(
    links: list[dict[str, str]], listing_type: str
) -> list[dict]:
    prefix = f"/{listing_type}/"
    seen: set[str] = set()
    subtypes: list[dict] = []
    for link in links:
        name = (link.get("name") or "").strip()
        href = (link.get("href") or "").strip()
        if not name or not href:
            continue
        path = href.split("hepsiemlak.com", 1)[-1]
        path = path.split("?", 1)[0]
        if not path.startswith(prefix):
            continue
        rest = path[len(prefix) :].strip("/")
        if not rest or "/" in rest:
            continue
        subtype_id = rest.replace("-", "_")
        if subtype_id in seen:
            continue
        seen.add(subtype_id)
        subtypes.append({"id": subtype_id, "name": name, "path": f"{prefix}{rest}"})
    return subtypes


def fetch_all_subcategories_with_selenium() -> dict[str, dict[str, list[dict]]]:
    """Tüm kategori/listing_type kombinasyonları için alt kategorileri Selenium ile çek"""
    from core.driver_manager import DriverManager

    config = get_hepsiemlak_config()
    all_subcategories: dict[str, dict[str, list[dict]]] = {}

    manager = DriverManager()
    driver = None

    try:
        driver = manager.start()

        for listing_type in ["satilik", "kiralik"]:
            all_subcategories[listing_type] = {}

            for category, path in config.categories[listing_type].items():
                url = f"{config.base_url}{path}"
                logger.info(f"Fetching: {listing_type}/{category} -> {url}")
                print(f"[>] Cekiliyor: {listing_type}/{category}")

                try:
                    driver.get(url)
                    time.sleep(4)
                    links = driver.execute_script(
                        """
                        return [...document.querySelectorAll('a.sub-category-link')].map((a) => ({
                          name: (a.querySelector('.sub-category-select-item') || a).innerText.trim(),
                          href: a.href || a.getAttribute('href') || ''
                        }));
                        """
                    )
                    subtypes = parse_hepsiemlak_subtype_links(links or [], listing_type)
                    all_subcategories[listing_type][category] = subtypes
                    print(f"   [+] {len(subtypes)} alt kategori bulundu")

                except Exception as e:
                    logger.error(f"Error fetching {category}: {e}")
                    all_subcategories[listing_type][category] = []

    except Exception as e:
        logger.error(f"Driver error: {e}")
    finally:
        # Driver'ı güvenli bir şekilde kapat
        if driver:
            try:
                driver.quit()
            except Exception:  # nosec
                pass
        try:
            manager.stop()
        except Exception:  # nosec
            pass

    return all_subcategories


def fetch_subtypes(listing_type: str, category: str) -> list[dict]:
    """JSON dosyasından alt kategorileri oku; dosya yoksa boş liste döndürür"""
    data = load_subcategories_from_json()
    return data.get(listing_type, {}).get(category, [])


def get_cached_subtypes(listing_type: str, category: str) -> list[dict] | None:
    """Cache kontrolü - JSON dosyası varsa veri döner"""
    if SUBCATEGORIES_JSON_PATH.exists():
        return fetch_subtypes(listing_type, category)
    return None


def ensure_subcategories_exist():
    """JSON dosyasi yoksa Selenium ile cek ve kaydet"""
    if not SUBCATEGORIES_JSON_PATH.exists():
        print("[!] Subcategories JSON dosyasi bulunamadi. Selenium ile cekiliyor...")
        data = fetch_all_subcategories_with_selenium()
        save_subcategories_to_json(data)
        print("[+] Subcategories kaydedildi!")
    else:
        print("[OK] Subcategories JSON dosyasi mevcut")


def refresh_subcategories():
    """Subcategories'i yeniden cek ve kaydet"""
    print("[*] Subcategories yenileniyor...")
    data = merge_subcategories(
        fetch_all_subcategories_with_selenium(),
        load_subcategories_from_json(),
    )
    save_subcategories_to_json(data)
    print("[+] Subcategories guncellendi!")


# CLI için
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--refresh":
        refresh_subcategories()
    else:
        ensure_subcategories_exist()
