# -*- coding: utf-8 -*-
"""
HepsiEmlak Subcategory Fetcher & Cache Manager
Selenium ile bir kez çeker, JSON'a kaydeder, sonra hep dosyadan okur
"""

import json
import os
import time
from typing import List, Dict, Optional
from pathlib import Path

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from core.config import get_hepsiemlak_config
from core.driver_manager import DriverManager
from utils.logger import get_logger
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

logger = get_logger(__name__)

# JSON dosya yolu
SUBCATEGORIES_JSON_PATH = Path(__file__).parent / "subcategories.json"


def load_subcategories_from_json() -> Dict[str, Dict[str, List[Dict]]]:
    """JSON dosyasından subcategories yükle"""
    if SUBCATEGORIES_JSON_PATH.exists():
        try:
            with open(SUBCATEGORIES_JSON_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"JSON okuma hatası: {e}")
    return {}


def save_subcategories_to_json(data: Dict[str, Dict[str, List[Dict]]]):
    """Subcategories'i JSON dosyasına kaydet"""
    try:
        with open(SUBCATEGORIES_JSON_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"Subcategories kaydedildi: {SUBCATEGORIES_JSON_PATH}")
    except Exception as e:
        logger.error(f"JSON yazma hatası: {e}")


def fetch_all_subcategories_with_selenium() -> Dict[str, Dict[str, List[Dict]]]:
    """
    Tüm kategori/listing_type kombinasyonları için subcategories çek.
    Bu fonksiyon sadece bir kez çalıştırılmalı (veya güncelleme gerektiğinde).
    """
    config = get_hepsiemlak_config()
    all_subcategories = {}
    
    manager = DriverManager()
    driver = None
    
    try:
        driver = manager.start()
        
        for listing_type in ["satilik", "kiralik"]:
            all_subcategories[listing_type] = {}
            
            for category, path in config.categories[listing_type].items():
                url = f"{config.base_url}{path}"
                logger.info(f"Fetching: {listing_type}/{category} -> {url}")
                print(f"📥 Çekiliyor: {listing_type}/{category}")
                
                try:
                    driver.get(url)
                    time.sleep(5)  # Sayfa yüklenme süresi artırıldı
                    
                    # Dropdown'ı bul ve aç - birden fazla deneme
                    dropdown_found = False
                    for attempt in range(3):
                        try:
                            dropdown = driver.find_element(By.CSS_SELECTOR, "section.categorySubSec .custom-select")
                            driver.execute_script("arguments[0].scrollIntoView(true);", dropdown)
                            time.sleep(0.5)
                            driver.execute_script("arguments[0].click();", dropdown)
                            time.sleep(2)  # Dropdown açılma süresi artırıldı
                            dropdown_found = True
                            break
                        except Exception as e:
                            if attempt < 2:
                                print(f"   ⚠️ Dropdown bulunamadı, tekrar deneniyor... ({attempt + 1}/3)")
                                time.sleep(2)
                            continue
                    
                    if not dropdown_found:
                        logger.info(f"No dropdown for {category}")
                        all_subcategories[listing_type][category] = []
                        continue
                    
                    # Alt kategorileri çek
                    subtypes = []
                    links = driver.find_elements(By.CSS_SELECTOR, "section.categorySubSec .sub-category-link")
                    
                    # Eğer link bulunamadıysa, dropdown listesini de dene
                    if not links:
                        links = driver.find_elements(By.CSS_SELECTOR, ".dropdown-lightbox .sub-category-link")
                    
                    for link in links:
                        try:
                            href = link.get_attribute("href") or ""
                            name_el = link.find_element(By.CSS_SELECTOR, ".sub-category-select-item")
                            name = name_el.text.strip() if name_el else ""
                            
                            if name and href:
                                path_part = href.replace(config.base_url, "")
                                subtype_id = path_part.split("/")[-1].replace("-", "_")
                                
                                subtypes.append({
                                    "id": subtype_id,
                                    "name": name,
                                    "path": path_part
                                })
                        except Exception as e:
                            continue
                    
                    all_subcategories[listing_type][category] = subtypes
                    print(f"   ✓ {len(subtypes)} alt kategori bulundu")
                    
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
            except Exception:
                pass
        try:
            manager.stop()
        except Exception:
            pass
    
    return all_subcategories


def fetch_subtypes(listing_type: str, category: str) -> List[Dict]:
    """
    JSON dosyasından subcategories oku.
    Dosya yoksa boş liste döner.
    """
    data = load_subcategories_from_json()
    return data.get(listing_type, {}).get(category, [])


def get_cached_subtypes(listing_type: str, category: str) -> Optional[List[Dict]]:
    """Cache kontrolü - JSON dosyası varsa veri döner"""
    if SUBCATEGORIES_JSON_PATH.exists():
        return fetch_subtypes(listing_type, category)
    return None


def ensure_subcategories_exist():
    """JSON dosyası yoksa Selenium ile çek ve kaydet"""
    if not SUBCATEGORIES_JSON_PATH.exists():
        print("⚠️ Subcategories JSON dosyası bulunamadı. Selenium ile çekiliyor...")
        data = fetch_all_subcategories_with_selenium()
        save_subcategories_to_json(data)
        print("✅ Subcategories kaydedildi!")
    else:
        print("✓ Subcategories JSON dosyası mevcut")


def refresh_subcategories():
    """Subcategories'i yeniden çek ve kaydet"""
    print("🔄 Subcategories yenileniyor...")
    data = fetch_all_subcategories_with_selenium()
    save_subcategories_to_json(data)
    print("✅ Subcategories güncellendi!")


# CLI için
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--refresh":
        refresh_subcategories()
    else:
        ensure_subcategories_exist()
