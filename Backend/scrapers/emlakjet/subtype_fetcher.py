# -*- coding: utf-8 -*-
"""EmlakJet alt kategori çekici ve önbellek yöneticisi"""

import json
import os
import time
from typing import List, Dict, Optional
from pathlib import Path

import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from core.driver_manager import DriverManager
from utils.logger import get_logger
from selenium.webdriver.common.by import By

logger = get_logger(__name__)

# JSON dosya yolu
SUBCATEGORIES_JSON_PATH = Path(__file__).parent / "subcategories.json"

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


def load_subcategories_from_json() -> Dict[str, Dict[str, List[Dict]]]:
    """JSON dosyasından subcategories yükle"""
    if SUBCATEGORIES_JSON_PATH.exists():
        try:
            with open(SUBCATEGORIES_JSON_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"JSON okuma hatası: {e}")
    return {}


def save_subcategories_to_json(data: Dict[str, Dict[str, List[Dict]]]):
    """Subcategories'i JSON dosyasına kaydet"""
    try:
        with open(SUBCATEGORIES_JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"Subcategories kaydedildi: {SUBCATEGORIES_JSON_PATH}")
    except Exception as e:
        logger.error(f"JSON yazma hatası: {e}")


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


def fetch_all_subcategories_with_selenium() -> Dict[str, Dict[str, List[Dict]]]:
    """Selenium ile tüm alt kategorileri çek"""
    all_subcategories: Dict[str, Dict[str, List[Dict]]] = {}
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

                    subtypes = []

                    # Yeni yapı: sidebar menüde ana kategori düğümü
                    # <div data-node-id="satilik-konut"> ve alt türler
                    # <div data-node-id="satilik-daire"><a href="/satilik-daire">Daire</a>
                    main_slug = path.strip("/").replace("/", "-")
                    try:
                        main_node = driver.find_element(
                            By.CSS_SELECTOR, f"[data-node-id='{main_slug}']"
                        )
                        sub_ul = main_node.find_element(
                            By.XPATH, "following-sibling::ul[1]"
                        )
                        sub_links = sub_ul.find_elements(
                            By.CSS_SELECTOR, "[data-node-id] a[href^='/']"
                        )

                        for link in sub_links:
                            try:
                                href = link.get_attribute("href") or ""
                                name = link.text.strip()

                                if name and href:
                                    subtype_path = href.replace(base_url, "")
                                    subtype_id = extract_subtype_id(subtype_path)

                                    subtypes.append(
                                        {
                                            "id": subtype_id,
                                            "name": name,
                                            "path": subtype_path,
                                        }
                                    )
                            except Exception:  # nosec
                                continue

                        # Eski yapı: styles_ulSubMenu seçicileri (geriye dönük uyumluluk)
                        if not subtypes:
                            submenu_items = driver.find_elements(
                                By.CSS_SELECTOR, "li.styles_subMenu2__BskGl"
                            )
                            for item in submenu_items:
                                try:
                                    main_link = item.find_element(By.CSS_SELECTOR, "a")
                                    main_href = main_link.get_attribute("href") or ""
                                    if path in main_href or main_href.endswith(path):
                                        sub_links_legacy = item.find_elements(
                                            By.CSS_SELECTOR,
                                            "ul.styles_ulSubMenu__E0zyf li.styles_subMenu2__BskGl a",
                                        )
                                        for legacy_link in sub_links_legacy:
                                            try:
                                                href = (
                                                    legacy_link.get_attribute("href")
                                                    or ""
                                                )
                                                span = legacy_link.find_element(
                                                    By.CSS_SELECTOR, "span"
                                                )
                                                name = span.text.split("(")[0].strip()
                                                if name and href:
                                                    subtype_path = href.replace(
                                                        base_url, ""
                                                    )
                                                    subtype_id = extract_subtype_id(
                                                        subtype_path
                                                    )
                                                    subtypes.append(
                                                        {
                                                            "id": subtype_id,
                                                            "name": name,
                                                            "path": subtype_path,
                                                        }
                                                    )
                                            except Exception:  # nosec
                                                continue
                                        break
                                except Exception:  # nosec
                                    continue
                    except Exception as e:
                        logger.warning(f"Alt kategori çekme hatası: {e}")

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


def fetch_subtypes(listing_type: str, category: str) -> List[Dict]:
    """JSON dosyasından alt kategorileri oku"""
    data = load_subcategories_from_json()
    return data.get(listing_type, {}).get(category, [])


def get_cached_subtypes(listing_type: str, category: str) -> Optional[List[Dict]]:
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
    data = fetch_all_subcategories_with_selenium()
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
