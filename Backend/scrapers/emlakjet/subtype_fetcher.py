"""EmlakJet alt kategori çekici ve önbellek yöneticisi"""

import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from utils.logger import get_logger

logger = get_logger(__name__)

# JSON dosya yolu
SUBCATEGORIES_JSON_PATH = Path(__file__).parent / "subcategories.json"
_SUBCATEGORIES_CACHE: tuple[tuple[str, int], dict[str, dict[str, list[dict]]]] | None = None

# Ana kategoriler ve URL'leri
MAIN_CATEGORIES = {
    "satilik": {
        "konut": "/satilik-konut",
        "arsa": "/satilik-arsa",
        "kat_karsiligi_arsa": "/kat-karsiligi-arsa",
        "isyeri": "/satilik-isyeri",
        "devren_isyeri": "/devren-isyeri",
        "turistik_tesis": "/satilik-turistik-tesis",
    },
    "kiralik": {
        "konut": "/kiralik-konut",
        "gunluk_kiralik": "/gunluk-kiralik-konut",
        "arsa": "/kiralik-arsa",
        "isyeri": "/kiralik-isyeri",
        "turistik_tesis": "/kiralik-turistik-tesis",
    },
}


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


def candidate_node_ids(path: str) -> list[str]:
    slug = path.strip("/").replace("/", "-")
    aliases = [slug, slug.replace("isyeri", "is-yeri"), slug.replace("is-yeri", "isyeri")]
    return list(dict.fromkeys(aliases))


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


def extract_subtype_id(path: str) -> str:
    """URL path'inden subtype ID çıkar"""
    # Path'i temizle
    path = path.strip("/")

    # İlan tipi prefix'ini kaldır
    prefixes = ["satilik-", "kiralik-", "devren-", "gunluk-kiralik-", "kat-karsiligi-"]
    for prefix in prefixes:
        if path.startswith(prefix):
            path = path[len(prefix) :]
            break

    # Tire'ları alt çizgiye çevir
    return path.replace("-", "_")


def fetch_all_subcategories_with_selenium() -> dict[str, dict[str, list[dict]]]:
    """Selenium ile tüm alt kategorileri çek"""
    from core.driver_manager import DriverManager

    all_subcategories: dict[str, dict[str, list[dict]]] = {}
    base_url = "https://www.emlakjet.com"

    manager = DriverManager()
    driver = None

    try:
        driver = manager.start()

        for listing_type, categories in MAIN_CATEGORIES.items():
            all_subcategories[listing_type] = {}
            print(f"\n{'=' * 60}")
            print(f"[*] {listing_type.upper()} KATEGORILERI")
            print("=" * 60)

            for category, path in categories.items():
                url = f"{base_url}{path}"
                print(f"\n[>] Kategori: {category} -> {url}")

                try:
                    driver.get(url)
                    time.sleep(3)  # Sayfa yüklensin

                    rows = driver.execute_script(
                        """
                        const slugs = arguments[0];
                        let parent = null;
                        for (const slug of slugs) {
                          parent = document.querySelector('[data-node-id=\"' + slug + '\"]');
                          if (parent) break;
                        }
                        if (!parent) return [];
                        const ul = parent.nextElementSibling;
                        if (!ul) return [];
                        return [...ul.querySelectorAll('[data-node-id] a[href^=\"/\"]')].map((a) => ({
                          name: (a.innerText || '').trim().split('\\n')[0],
                          href: a.getAttribute('href') || ''
                        }));
                        """,
                        candidate_node_ids(path),
                    )
                    subtypes = []
                    for row in rows or []:
                        name = (row.get("name") or "").strip()
                        href = (row.get("href") or "").strip()
                        if not name or not href:
                            continue
                        subtype_path = href.replace(base_url, "")
                        subtypes.append(
                            {
                                "id": extract_subtype_id(subtype_path),
                                "name": name,
                                "path": subtype_path,
                            }
                        )

                    all_subcategories[listing_type][category] = subtypes

                    if subtypes:
                        print(f"   [+] {len(subtypes)} alt kategori bulundu:")
                        for s in subtypes[:5]:  # Ilk 5'ini goster
                            print(f"      - {s['name']} ({s['path']})")
                        if len(subtypes) > 5:
                            print(f"      ... ve {len(subtypes) - 5} tane daha")
                    else:
                        print("   [!] Alt kategori bulunamadi")

                    # İstek hız sınırlama
                    time.sleep(2)

                except Exception as e:
                    logger.error(f"Kategori çekme hatası ({category}): {e}")
                    all_subcategories[listing_type][category] = []

    except Exception as e:
        logger.error(f"Driver hatası: {e}")
    finally:
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
    """JSON dosyasından alt kategorileri oku"""
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
        print(
            "[!] EmlakJet subcategories JSON dosyasi bulunamadi. Selenium ile cekiliyor..."
        )
        data = fetch_all_subcategories_with_selenium()
        save_subcategories_to_json(data)
        print("[+] Subcategories kaydedildi!")
    else:
        print("[OK] EmlakJet subcategories JSON dosyasi mevcut")


def refresh_subcategories():
    """Subcategories'i yeniden cek ve kaydet"""
    print("[*] EmlakJet subcategories yenileniyor...")
    data = merge_subcategories(
        fetch_all_subcategories_with_selenium(),
        load_subcategories_from_json(),
    )
    save_subcategories_to_json(data)
    print("[+] Subcategories guncellendi!")

    # Ozet yazdir
    print("\n" + "=" * 60)
    print("[i] OZET")
    print("=" * 60)
    for listing_type, categories in data.items():
        total = sum(len(subs) for subs in categories.values())
        print(f"\n{listing_type.upper()}: {total} alt kategori")
        for cat, subs in categories.items():
            if subs:
                print(f"   - {cat}: {len(subs)} alt kategori")


# CLI icin
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--refresh":
        refresh_subcategories()
    elif len(sys.argv) > 1 and sys.argv[1] == "--test":
        # Test: mevcut verileri goster
        data = load_subcategories_from_json()
        if data:
            print("[i] Mevcut subcategories:")
            for lt, cats in data.items():
                print(f"\n{lt.upper()}:")
                for cat, subs in cats.items():
                    print(f"  {cat}: {len(subs)} alt kategori")
        else:
            print("[!] JSON dosyasi bulunamadi veya bos")
    else:
        ensure_subcategories_exist()
