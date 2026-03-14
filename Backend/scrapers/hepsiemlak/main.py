# -*- coding: utf-8 -*-
"""HepsiEmlak Ana Scraper - gizli mod"""

import time
import random
import re
from typing import Dict, List, Any, Optional, Set
from urllib.parse import urlparse

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.remote.webdriver import WebDriver

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from core.base_scraper import BaseScraper
from core.driver_manager import DriverManager
from core.selectors import get_selectors, get_common_selectors
from core.config import get_hepsiemlak_config
from core.failed_pages_tracker import FailedPagesTracker, FailedPageInfo, failed_pages_tracker
from utils.logger import get_logger, TaskLogLayout

from .parsers import KonutParser, ArsaParser, IsyeriParser, DevremulkParser, TuristikParser

logger = get_logger(__name__)
task_log = TaskLogLayout(logger)


def _get_expected_hepsiemlak_subtype_slugs(listing_type: str, category: str) -> Set[str]:
    """HepsiEmlak kategori filtresi icin beklenen subtype slug listesini don."""
    expected_slugs: Set[str] = set()
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
                path_parts = [part for part in subtype_path.strip("/").split("/") if part]
                if len(path_parts) >= 2:
                    expected_slugs.add(path_parts[-1])
    except Exception:
        # JSON yoksa veya okunamazsa URL tabanli zorlayici filtreleme yapmayiz.
        pass

    if expected_slugs:
        expected_slugs.add(category.replace("_", "-").lower())

    return expected_slugs


def _extract_hepsiemlak_subtype_slug_from_url(listing_url: str, listing_type: str) -> Optional[str]:
    """Ilan URL'sinden subtype slug'i cikar."""
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
        if listing_type_marker not in first_segment and first_segment != listing_type.lower():
            return None

        # /<lokasyon>-satilik/<subtype-or-id> veya /satilik/<subtype-or-id> desenleri
        if len(parts) < 2:
            return ""

        return parts[1].strip().lower()
    except Exception:
        return None


def _matches_hepsiemlak_filters(
    listing_url: str,
    listing_type: str,
    category: str,
    alt_kategori: Optional[str],
    expected_subtypes: Set[str],
) -> bool:
    """URL bazli listing_type/category/subtype filtre dogrulamasi."""
    extracted_slug = _extract_hepsiemlak_subtype_slug_from_url(listing_url, listing_type)
    if extracted_slug is None:
        return False

    selected_subtype = (alt_kategori or "").replace("_", "-").strip().lower()
    if selected_subtype:
        return extracted_slug == selected_subtype

    # Konut ana sayfasinda slug olmayabilir: /<lokasyon>-satilik/<ilan-id>
    if category == "konut" and (not extracted_slug or extracted_slug[0].isdigit()):
        return True

    if not expected_subtypes:
        return True

    return extracted_slug in expected_subtypes


def save_listings_to_db(
    db,
    listings: List[Dict],
    platform: str,
    kategori: str,
    ilan_tipi: str,
    alt_kategori: str = None,
    scrape_session_id: int = None,
    log_db_save: bool = True,
):
    """Ä°lan listesini veritabanÄ±na kaydet (upsert mantÄ±ÄŸÄ± ile)"""
    if not db:
        return 0, 0, 0

    try:
        from database import crud
        new_count = 0
        updated_count = 0
        unchanged_count = 0
        records_to_save = listings

        if platform == "hepsiemlak":
            expected_subtypes = _get_expected_hepsiemlak_subtype_slugs(ilan_tipi, kategori)
            filtered_records: List[Dict] = []
            filtered_out = 0

            for data in listings:
                listing_url = data.get("ilan_linki") or data.get("ilan_url")
                if _matches_hepsiemlak_filters(
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

        for data in records_to_save:
            listing, status = crud.upsert_listing(
                db,
                data=data,
                platform=platform,
                kategori=kategori,
                ilan_tipi=ilan_tipi,
                alt_kategori=alt_kategori,
                scrape_session_id=scrape_session_id
            )
            if status == 'created':
                new_count += 1
            elif status == 'updated':
                updated_count += 1
            elif status == 'unchanged':
                unchanged_count += 1

        db.commit()
        if log_db_save:
            logger.info(f"DB save: {new_count} new, {updated_count} updated, {unchanged_count} unchanged")
        return new_count, updated_count, unchanged_count
    except Exception as e:
        logger.error(f"DB save error: {e}")
        db.rollback()
        return 0, 0, 0


class HepsiemlakScraper(BaseScraper):
    """HepsiEmlak platformu ana scraper sÄ±nÄ±fÄ±"""
    
    CATEGORY_PARSERS = {
        'konut': KonutParser,
        'arsa': ArsaParser,
        'isyeri': IsyeriParser,
        'devremulk': DevremulkParser,
        'turistik_isletme': TuristikParser,
    }
    
    def __init__(
        self,
        driver: WebDriver,
        listing_type: str = "satilik",  # 'satilik' veya 'kiralik'
        category: str = "konut",
        subtype_path: Optional[str] = None,  # Alt kategori URL path'i
        selected_cities: Optional[List[str]] = None,
        selected_districts: Optional[Dict[str, List[str]]] = None  # Ä°l -> [Ä°lÃ§eler] mapping
    ):
        base_config = get_hepsiemlak_config()
        
        # Subtype path varsa onu kullan, yoksa ana kategori
        if subtype_path:
            category_path = subtype_path
            logger.info(f"Using subtype path: {subtype_path}")
        else:
            category_path = base_config.categories.get(listing_type, {}).get(category, '')
        
        base_url = base_config.base_url + category_path
        
        super().__init__(driver, base_url, "hepsiemlak", category)

        self.listing_type = listing_type
        self.hepsiemlak_config = base_config
        self.selected_cities = selected_cities or []
        self.selected_districts = selected_districts or {}  # Ä°lÃ§e filtreleme
        self.subtype_path = subtype_path  # Kaydet
        self.total_new_listings = 0  # Global kÃ¼mÃ¼latif yeni ilan sayacÄ±
        self.current_category = category

        # VeritabanÄ± desteÄŸi (endpoints.py tarafÄ±ndan ayarlanÄ±r)
        self.db = None
        self.scrape_session_id = None
        self.total_scraped_count = 0
        self.new_listings_count = 0
        self.duplicate_count = 0

        # Uygun parser'Ä± baÅŸlat
        parser_class = self.CATEGORY_PARSERS.get(category, KonutParser)
        self.parser = parser_class()
    
    @property
    def subtype_name(self) -> Optional[str]:
        """Dosya adlandÄ±rma iÃ§in subtype_path'inden alt kategori adÄ±nÄ± Ã§Ä±kar"""
        if self.subtype_path:
            # /satilik/daire -> daire
            parts = self.subtype_path.strip('/').split('/')
            if len(parts) >= 2:
                return parts[-1].replace('-', '_')
        return None
    def _build_location_url(self, location_name: str) -> str:
        location_slug = self._normalize_text(location_name)
        if self.subtype_path:
            parts = self.subtype_path.strip('/').split('/')
            if len(parts) >= 2:
                return f"https://www.hepsiemlak.com/{location_slug}-{self.listing_type}/{parts[-1]}"
            return f"https://www.hepsiemlak.com/{location_slug}-{self.listing_type}"

        category_path = self.hepsiemlak_config.categories.get(self.listing_type, {}).get(self.current_category, '')
        if category_path:
            parts = category_path.strip('/').split('/')
            if len(parts) > 1:
                return f"https://www.hepsiemlak.com/{location_slug}-{self.listing_type}/{parts[-1]}"
        return f"https://www.hepsiemlak.com/{location_slug}-{self.listing_type}"

    def _log_location_start(self, location_name: str, location_url: str) -> None:
        task_log.section(
            f"ğŸ“ TaranÄ±yor: {location_name}",
            f"ğŸŒ {location_url}",
            "ğŸ§­ YÃ¶ntem: selenium",
        )

    def _log_location_plan(self, location_name: str, pages_to_scrape: int) -> None:
        task_log.line(f"{location_name}: scraping {pages_to_scrape} pages via selenium")
        task_log.line(f"ğŸ“„ {pages_to_scrape} sayfa taranacak")

    def _log_page_start(self, location_name: str, page_num: int, total_pages: int) -> None:
        task_log.line(f"ğŸ” [{page_num}/{total_pages}] {location_name} - Sayfa {page_num} taranÄ±yor...")

    def _log_page_result(self, page_num: int, extracted_count: int, new_count: int, updated_count: int, unchanged_count: int) -> None:
        task_log.line(f"   âœ… Sayfa {page_num}: {extracted_count} ilan Ã§Ä±karÄ±ldÄ±")
        task_log.line(f"   ğŸ’¾ Sayfa {page_num}: {new_count} yeni, {updated_count} gÃ¼ncellendi, {unchanged_count} deÄŸiÅŸmedi")

    def _log_location_complete(self, location_name: str, listing_count: int) -> None:
        task_log.line(f"âœ… {location_name} tamamlandÄ± - {listing_count} ilan iÅŸlendi")

    def _log_retry_round(self, retry_round: int, max_retries: int, failed_count: int) -> None:
        task_log.section(
            f"ğŸ”„ YENÄ°DEN DENEME #{retry_round}/{max_retries}",
            f"ğŸ“Š {failed_count} baÅŸarÄ±sÄ±z sayfa tekrar taranacak",
        )

    def _log_retry_summary(self, successful_retries: int, failed_count: int) -> None:
        task_log.section(
            "ğŸ“Š RETRY Ã–ZETÄ°",
            f"   âœ… BaÅŸarÄ±lÄ± retry: {successful_retries}",
            f"   âŒ Kalan baÅŸarÄ±sÄ±z: {failed_count}",
        )

    def _log_final_summary(self, stopped_early: bool, city_count: int, total_listings: int) -> None:
        if stopped_early:
            task_log.section(
                "âš ï¸ ERKEN DURDURULDU",
                f"Taranan Åehir SayÄ±sÄ±: {city_count}",
                f"Toplam Ä°lan SayÄ±sÄ±: {total_listings}",
                level="warning",
            )
        elif total_listings > 0:
            task_log.section(
                "TARAMA BAÅARIYLA TAMAMLANDI",
                f"Taranan Åehir SayÄ±sÄ±: {city_count}",
                f"Toplam Ä°lan SayÄ±sÄ±: {total_listings}",
            )
        else:
            task_log.section("HIC ILAN BULUNAMADI", level="warning")
    
    def extract_listing_data(self, container) -> Optional[Dict[str, Any]]:
        """Kategori parser'Ä± ile ilan verisini Ã§Ä±kar"""
        return self.parser.extract_listing_data(container)
    
    def parse_category_details(self, quick_info: str, title: str) -> Dict[str, Any]:
        """HepsiEmlak iÃ§in kullanÄ±lmaz - parse iÅŸlemi extract_category_data ile yapÄ±lÄ±r"""
        return {}
    
    def get_cities(self) -> List[str]:
        """TÃ¼m ÅŸehirleri al ve kullanÄ±cÄ±nÄ±n seÃ§mesini saÄŸla"""
        print(f"\n{self.category.capitalize()} sitesine gidiliyor...")
        self.driver.get(self.base_url)
        time.sleep(5)  # HepsiEmlak iÃ§in sabit 5 saniye - sayfa tam yÃ¼klensin
        
        try:
            # Åehir dropdown'Ä±nÄ± bul
            city_dropdown_sel = self.common_selectors.get("city_dropdown")
            city_dropdown = self.wait_for_clickable(city_dropdown_sel)
            
            if not city_dropdown:
                logger.error("Åehir dropdown'Ä± bulunamadÄ±")
                return []
            
            # JS click ile menÃ¼yÃ¼ aÃ§ (Selenium'un objeye tÄ±klayamama riskine karÅŸÄ±)
            self.driver.execute_script("arguments[0].click();", city_dropdown)
            print("Åehir dropdown'Ä± aÃ§Ä±ldÄ±...")
            time.sleep(3)  # Dropdown aÃ§Ä±lmasÄ± iÃ§in 3 saniye
            
            # Dropdown'Ä± geniÅŸlet
            city_list_sel = self.common_selectors.get("city_list")
            dropdown_container = self.wait_for_element(city_list_sel)
            
            if dropdown_container:
                self.driver.execute_script("""
                    var container = arguments[0];
                    container.style.maxHeight = 'none';
                    container.style.overflow = 'visible';
                    container.style.height = 'auto';
                """, dropdown_container)
            time.sleep(2)  # Liste geniÅŸletme sonrasÄ± bekleme
            
            if not dropdown_container:
                logger.error("TÄ±klama sonrasÄ± ÅŸehir listesi gÃ¶rÃ¼ntÃ¼lenemedi")
                return []
            
            # Åehir Ã¶ÄŸelerini al
            city_item_sel = self.common_selectors.get("city_item")
            city_link_sel = self.common_selectors.get("city_link")
            
            city_items = self.driver.find_elements(By.CSS_SELECTOR, city_item_sel)
            
            cities = []
            for city_item in city_items:
                try:
                    city_link = city_item.find_element(By.CSS_SELECTOR, city_link_sel)
                    city_name = city_link.text.strip()
                    if city_name and city_name != "Ä°l SeÃ§iniz" and city_name not in cities:
                        cities.append(city_name)
                except:
                    continue
            
            cities.sort()
            
            # Åehirleri 4 sÃ¼tunda gÃ¶ster
            print("\n" + "=" * 80)
            print("TÃœM ÅEHÄ°RLER")
            print("=" * 80)
            
            cols = 4
            col_width = 20
            for i in range(0, len(cities), cols):
                row = ""
                for j in range(cols):
                    idx = i + j
                    if idx < len(cities):
                        row += f"{idx + 1:2d}. {cities[idx]:<{col_width - 4}}"
                print(row)
            
            print(f"\nToplam {len(cities)} ÅŸehir bulundu.")
            
            # Dropdown'Ä± kapat
            try:
                self.driver.execute_script("document.elementFromPoint(10, 10).click();")
            except:
                pass
            self.random_short_wait()  # Gizli mod
            
            return cities
            
            return cities
            
        except Exception as e:
            logger.error(f"Error getting cities: {e}")
            return []
            
    def get_cities_api(self) -> List[str]:
        """API iÃ§in ÅŸehir listesi al (etkileÅŸimsiz)"""
        return self.get_cities()
    
    def select_cities(self, cities: List[str]) -> List[str]:
        """KullanÄ±cÄ±nÄ±n birden fazla ÅŸehir seÃ§mesini saÄŸla"""
        selected = []
        
        print("\n" + "=" * 50)
        print("ÅEHÄ°R SEÃ‡Ä°M SEÃ‡ENEKLERÄ°")
        print("=" * 50)
        print("1. Tek tek ÅŸehir seÃ§ (Ã¶rn: 1,3,5)")
        print("2. AralÄ±k seÃ§ (Ã¶rn: 1-5)")
        print("3. TÃ¼m ÅŸehirleri seÃ§")
        print("4. Åehir sil")
        print("5. SeÃ§imi bitir")
        
        while True:
            print(f"\nSeÃ§ili ÅŸehirler ({len(selected)}): {selected}")
            option = input("\nSeÃ§enek (1-5): ").strip()
            
            if option == "5":
                if selected:
                    print(f"\nSeÃ§im tamamlandÄ±: {', '.join(selected)}")
                    return selected
                else:
                    print("En az bir ÅŸehir seÃ§melisiniz!")
            
            elif option == "3":
                selected = cities.copy()
                print("TÃ¼m ÅŸehirler seÃ§ildi!")
            
            elif option == "4":
                if not selected:
                    print("Silinecek ÅŸehir yok!")
                    continue
                
                print("\nMevcut seÃ§ili ÅŸehirler:")
                for i, city in enumerate(selected, 1):
                    print(f"{i}. {city}")
                
                delete_input = input("\nSilmek istediÄŸiniz numaralarÄ± girin: ").strip()
                indices = self._parse_selection_input(delete_input, len(selected))
                
                # Ä°ndeksleri korumak iÃ§in ters sÄ±rada sil
                for idx in sorted(indices, reverse=True):
                    removed = selected.pop(idx - 1)
                    print(f"âœ“ {removed} silindi")
            
            elif option == "2":
                range_input = input("AralÄ±k girin (Ã¶rn: 1-5): ").strip()
                indices = self._parse_selection_input(range_input, len(cities))
                for idx in indices:
                    if cities[idx - 1] not in selected:
                        selected.append(cities[idx - 1])
                print(f"{len(indices)} ÅŸehir eklendi.")
            
            elif option == "1":
                user_input = input("Åehir numaralarÄ±nÄ± girin (Ã¶rn: 1,3,5): ").strip()
                indices = self._parse_selection_input(user_input, len(cities))
                for idx in indices:
                    if cities[idx - 1] not in selected:
                        selected.append(cities[idx - 1])
                        print(f"SeÃ§ilen: {cities[idx - 1]}")
            
            else:
                print("GeÃ§ersiz seÃ§enek!")
        
        return selected
            
    def select_cities_api(self, all_cities: List[str], target_cities: Optional[List[str]] = None) -> List[str]:
        """API iÃ§in ÅŸehir seÃ§"""
        if not target_cities:
            return []
        
        selected = []
        for city in target_cities:
            # DoÄŸrudan eÅŸleÅŸtirme
            if city in all_cities:
                selected.append(city)
                continue
                
            # BÃ¼yÃ¼k/kÃ¼Ã§Ã¼k harf duyarsÄ±z eÅŸleÅŸtirme
            found = False
            for ac in all_cities:
                if ac.lower() == city.lower():
                    selected.append(ac)
                    found = True
                    break
            if not found:
                 logger.warning(f"Åehir bulunamadÄ±: {city}")
        
        return selected
    
    def select_single_city(self, city_name: str) -> bool:
        """Tek bir ÅŸehir seÃ§ - doÄŸrudan ÅŸehir URL'ine git"""
        try:
            import unicodedata
            
            # Unicode normalizasyonu (NFC -> composed form)
            city_slug = unicodedata.normalize('NFC', city_name)
            
            # TÃ¼rkÃ§e karakter dÃ¶nÃ¼ÅŸÃ¼mleri - Ã¶nce bÃ¼yÃ¼k harfleri Ã§evir
            tr_upper = {'Ä°': 'i', 'I': 'i', 'Ä': 'g', 'Ãœ': 'u', 'Å': 's', 'Ã–': 'o', 'Ã‡': 'c'}
            for tr, en in tr_upper.items():
                city_slug = city_slug.replace(tr, en)
            
            # Sonra kÃ¼Ã§Ã¼k harfe Ã§evir ve kÃ¼Ã§Ã¼k TÃ¼rkÃ§e karakterleri dÃ¶nÃ¼ÅŸtÃ¼r
            city_slug = city_slug.lower()
            tr_lower = {'Ä±': 'i', 'ÄŸ': 'g', 'Ã¼': 'u', 'ÅŸ': 's', 'Ã¶': 'o', 'Ã§': 'c'}
            for tr, en in tr_lower.items():
                city_slug = city_slug.replace(tr, en)
            
            city_slug = city_slug.replace(' ', '-')
            
            # HepsiEmlak URL formatÄ±: ayas-kiralik/mustakil-ev (ÅŸehir-tip/subtype)
            # Subtype path varsa: ÅŸehir-tip/subtype
            # Subtype yoksa: ÅŸehir-tip (konut ana kategori) veya ÅŸehir-tip/arsa
            if self.subtype_path:
                # Subtype path: /kiralik/mustakil-ev -> mustakil-ev
                path_parts = self.subtype_path.split('/')
                # path_parts: ['', 'kiralik', 'mustakil-ev']
                if len(path_parts) >= 3:
                    subtype_slug = path_parts[2]  # mustakil-ev
                    city_url = f"https://www.hepsiemlak.com/{city_slug}-{self.listing_type}/{subtype_slug}"
                else:
                    city_url = f"https://www.hepsiemlak.com/{city_slug}-{self.listing_type}"
            else:
                # Ana kategori iÃ§in config'den path al
                category_path = self.hepsiemlak_config.categories.get(self.listing_type, {}).get(self.current_category, '')
                # /kiralik -> ÅŸehir-kiralik (konut)
                # /kiralik/arsa -> ÅŸehir-kiralik/arsa
                if category_path:
                    parts = category_path.split('/')
                    if len(parts) > 2:
                        # arsa, isyeri, devremulk, turistik-isletme
                        city_url = f"https://www.hepsiemlak.com/{city_slug}-{self.listing_type}/{parts[2]}"
                    else:
                        # konut (ana kategori)
                        city_url = f"https://www.hepsiemlak.com/{city_slug}-{self.listing_type}"
                else:
                    city_url = f"https://www.hepsiemlak.com/{city_slug}-{self.listing_type}"

            self.driver.get(city_url)
            time.sleep(5)  # Sayfa tam yÃ¼klensin
            
            # URL doÄŸru mu kontrol et
            current_url = self.driver.current_url
            if city_slug in current_url:
                return True
            else:
                task_log.line(f"âš ï¸ {city_name} sayfasÄ±na gidilemedi. URL: {current_url}", level="warning")
                return False
            
        except Exception as e:
            task_log.line(f"Error selecting city {city_name}: {e}", level="error")
            return False

    @staticmethod
    def normalize_string(s: str) -> str:
        """TÃ¼rkÃ§e karakter normalize - fuzzy matching iÃ§in"""
        import unicodedata
        s = s.lower().strip()
        # TÃ¼rkÃ§e karakterleri deÄŸiÅŸtir
        replacements = {'Ä±': 'i', 'ÄŸ': 'g', 'Ã¼': 'u', 'ÅŸ': 's', 'Ã¶': 'o', 'Ã§': 'c', 'Ä°': 'i'}
        for old, new in replacements.items():
            s = s.replace(old, new)
        return unicodedata.normalize('NFKD', s)

    def _normalize_text(self, text: str) -> str:
        """URL iÃ§in TÃ¼rkÃ§e karakterleri dÃ¶nÃ¼ÅŸtÃ¼r ve slug oluÅŸtur"""
        import unicodedata
        text = unicodedata.normalize('NFC', text)
        replacements = {
            'Ä°': 'i', 'I': 'i', 'Ä': 'g', 'Ãœ': 'u', 'Å': 's', 'Ã–': 'o', 'Ã‡': 'c',
            'Ä±': 'i', 'ÄŸ': 'g', 'Ã¼': 'u', 'ÅŸ': 's', 'Ã¶': 'o', 'Ã§': 'c'
        }
        for tr, en in replacements.items():
            text = text.replace(tr, en)
        return text.lower().replace(' ', '-')

    def get_district_urls_from_dropdown(self, city_name: str) -> Dict[str, str]:
        """Åehir sayfasÄ±ndaki ilÃ§e dropdown'Ä±ndan gerÃ§ek URL'leri Ã§ek ve {ilÃ§e_adÄ±: url} sÃ¶zlÃ¼ÄŸÃ¼ dÃ¶ndÃ¼r"""
        district_urls = {}
        
        try:
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            
            # Ã–nce ÅŸehir sayfasÄ±na git
            city_slug = self._normalize_text(city_name)
            
            # HepsiEmlak URL formatÄ±: sehir-kiralik/subtype
            if self.subtype_path:
                path_parts = self.subtype_path.strip('/').split('/')
                if len(path_parts) >= 2:
                    subtype_slug = path_parts[1]  # kiralik/daire -> daire
                    city_url = f"https://www.hepsiemlak.com/{city_slug}-{self.listing_type}/{subtype_slug}"
                else:
                    city_url = f"https://www.hepsiemlak.com/{city_slug}-{self.listing_type}"
            else:
                category_path = self.hepsiemlak_config.categories.get(self.listing_type, {}).get(self.current_category, '')
                if category_path:
                    parts = category_path.strip('/').split('/')
                    if len(parts) > 1:
                        city_url = f"https://www.hepsiemlak.com/{city_slug}-{self.listing_type}/{parts[1]}"
                    else:
                        city_url = f"https://www.hepsiemlak.com/{city_slug}-{self.listing_type}"
                else:
                    city_url = f"https://www.hepsiemlak.com/{city_slug}-{self.listing_type}"
            
            self.driver.get(city_url)
            time.sleep(3)
            
            # Ä°lÃ§e dropdown'Ä±nÄ± bul ve tÄ±kla
            try:
                # "Ä°lÃ§e SeÃ§iniz" placeholder'Ä± olan dropdown container'Ä±nÄ± bul
                dropdown = None
                try:
                    # Placeholder span'Ä±nÄ± bul ve Ã¼st konteyner'a tÄ±kla
                    placeholder = self.driver.find_element(
                        By.XPATH, "//span[contains(@class, 'he-select-base__placeholder') and contains(text(), 'Ä°lÃ§e')]"
                    )
                    dropdown = placeholder.find_element(By.XPATH, "..")  # Ãœst eleman
                except:
                    # Alternatif: doÄŸrudan container'Ä± bul
                    containers = self.driver.find_elements(By.CSS_SELECTOR, "div.he-select-base__container")
                    for cont in containers:
                        if "Ä°lÃ§e" in cont.text:
                            dropdown = cont
                            break

                if not dropdown:
                    task_log.line("âš ï¸ Ä°lÃ§e dropdown'Ä± bulunamadÄ±", level="warning")
                    return district_urls

                # Dropdown'Ä± aÃ§
                self.driver.execute_script("arguments[0].click();", dropdown)
                time.sleep(2)  # Liste yÃ¼klensin

                # JavaScript ile tÃ¼m ilÃ§eleri bir seferde al (scroll gerektirmez)
                try:
                    # TÃ¼m linkleri JS ile Ã§ek - gÃ¶rÃ¼nÃ¼rlÃ¼k Ã¶nemli deÄŸil
                    all_districts = self.driver.execute_script("""
                        var results = [];
                        var links = document.querySelectorAll('li.he-multiselect__list-item a.js-county-filter__list-link');
                        links.forEach(function(link) {
                            var name = link.textContent.trim() || link.innerText.trim();
                            var href = link.getAttribute('href');
                            if (name && href) {
                                results.push({name: name, href: href});
                            }
                        });
                        return results;
                    """)

                    for item in all_districts:
                        district_urls[item['name']] = item['href']

                    task_log.line(f"   ğŸ“œ {len(district_urls)} ilÃ§e JS ile toplandÄ±")

                except Exception as js_error:
                    task_log.line(f"JS ile ilÃ§e alma hatasÄ±: {js_error}", level="warning")

                # Dropdown'Ä± kapat
                try:
                    self.driver.find_element(By.TAG_NAME, "body").click()
                except:
                    pass

                task_log.line(f"ğŸ“Š {len(district_urls)} ilÃ§e URL'i bulundu")

            except Exception as e:
                task_log.line(f"Dropdown'dan URL Ã§ekme hatasÄ±: {e}", level="warning")
            
            return district_urls
            
        except Exception as e:
            task_log.line(f"get_district_urls_from_dropdown hatasÄ±: {e}", level="error")
            return district_urls

    def select_single_district(self, district_name: str) -> bool:
        """Ä°lÃ§e iÃ§in doÄŸrudan URL'e git - dropdown kullanma"""
        try:
            import unicodedata

            # Unicode normalizasyonu (NFC -> composed form)
            district_slug = unicodedata.normalize('NFC', district_name)

            # TÃ¼rkÃ§e karakter dÃ¶nÃ¼ÅŸÃ¼mleri - Ã¶nce bÃ¼yÃ¼k harfleri Ã§evir
            tr_upper = {'Ä°': 'i', 'I': 'i', 'Ä': 'g', 'Ãœ': 'u', 'Å': 's', 'Ã–': 'o', 'Ã‡': 'c'}
            for tr, en in tr_upper.items():
                district_slug = district_slug.replace(tr, en)

            # Sonra kÃ¼Ã§Ã¼k harfe Ã§evir ve kÃ¼Ã§Ã¼k TÃ¼rkÃ§e karakterleri dÃ¶nÃ¼ÅŸtÃ¼r
            district_slug = district_slug.lower()
            tr_lower = {'Ä±': 'i', 'ÄŸ': 'g', 'Ã¼': 'u', 'ÅŸ': 's', 'Ã¶': 'o', 'Ã§': 'c'}
            for tr, en in tr_lower.items():
                district_slug = district_slug.replace(tr, en)

            district_slug = district_slug.replace(' ', '-')

            # HepsiEmlak URL formatÄ±: ilce-kiralik/subtype (ilce-tip/subtype)
            if self.subtype_path:
                path_parts = self.subtype_path.split('/')
                if len(path_parts) >= 3:
                    subtype_slug = path_parts[2]
                    district_url = f"https://www.hepsiemlak.com/{district_slug}-{self.listing_type}/{subtype_slug}"
                else:
                    district_url = f"https://www.hepsiemlak.com/{district_slug}-{self.listing_type}"
            else:
                category_path = self.hepsiemlak_config.categories.get(self.listing_type, {}).get(self.current_category, '')
                if category_path:
                    parts = category_path.split('/')
                    if len(parts) > 2:
                        district_url = f"https://www.hepsiemlak.com/{district_slug}-{self.listing_type}/{parts[2]}"
                    else:
                        district_url = f"https://www.hepsiemlak.com/{district_slug}-{self.listing_type}"
                else:
                    district_url = f"https://www.hepsiemlak.com/{district_slug}-{self.listing_type}"

            self.driver.get(district_url)
            time.sleep(5)  # Sayfa tam yÃ¼klensin

            # URL doÄŸru mu kontrol et
            current_url = self.driver.current_url
            if district_slug in current_url:
                return True
            else:
                task_log.line(f"âš ï¸ {district_name} sayfasÄ±na gidilemedi. URL: {current_url}", level="warning")
                return False

        except Exception as e:
            task_log.line(f"Error selecting district {district_name}: {e}", level="error")
            return False

    def search_listings(self) -> bool:
        """Arama butonuna tÄ±kla ve sonuÃ§larÄ± bekle"""
        try:
            search_selectors = self.common_selectors.get("search_buttons", [])
            
            for selector in search_selectors:
                try:
                    search_button = self.wait_for_clickable(selector, timeout=5)
                    if search_button:
                        self.driver.execute_script("arguments[0].click();", search_button)
                        print("Arama yapÄ±lÄ±yor...")
                        self.random_long_wait()  # Gizli mod: arama sonrasÄ±
                        
                        # SonuÃ§larÄ± bekle
                        results_sel = self.common_selectors.get("listing_results")
                        self.wait_for_element(results_sel)
                        return True
                except:
                    continue
            
            print("Arama butonu bulunamadÄ±")
            return False
            
        except Exception as e:
            logger.error(f"Search error: {e}")
            return False
    
    def get_total_pages(self) -> int:
        """Sayfalamadan toplam sayfa sayÄ±sÄ±nÄ± al"""
        try:
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            
            # Ã–nce toplam ilan sayÄ±sÄ±nÄ± kontrol et - 24 veya daha az ise pagination olmaz
            try:
                listing_count_element = self.driver.find_element(
                    By.CSS_SELECTOR, "span.applied-filters__count"
                )
                count_text = listing_count_element.text.strip()
                # "iÃ§in 2.972 ilan bulundu" -> 2972
                # TÃ¼rkÃ§e binlik ayÄ±rÄ±cÄ± noktayÄ± kaldÄ±r
                import re
                # Ã–nce noktalarÄ± kaldÄ±r (binlik ayÄ±rÄ±cÄ±), sonra sayÄ±yÄ± bul
                count_text_clean = count_text.replace('.', '')
                match = re.search(r'(\d+)', count_text_clean)
                if match:
                    total_listings = int(match.group(1))
                    if total_listings <= 24:
                        print(f"ğŸ“Š Toplam {total_listings} ilan - tek sayfa (pagination yok)")
                        return 1
                    else:
                        print(f"ğŸ“Š Toplam {total_listings} ilan tespit edildi")
            except Exception:
                pass  # Ä°lan sayÄ±sÄ± bulunamazsa pagination kontrolÃ¼ne geÃ§
            
            # Sayfalama kontrolÃ¼ - ul.he-pagination__links iÃ§indeki a elementleri
            max_retries = 5
            page_links = []

            for retry in range(max_retries):
                try:
                    wait = WebDriverWait(self.driver, 10)
                    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "ul.he-pagination__links")))
                    page_links = self.driver.find_elements(By.CSS_SELECTOR, "ul.he-pagination__links a")
                    if page_links:
                        print(f"âœ“ Pagination bulundu: {len(page_links)} link")
                        break
                except Exception:
                    pass

                if retry < max_retries - 1:
                    print(f"âš ï¸ Pagination bulunamadÄ±, tekrar deneniyor... ({retry + 1}/{max_retries})")
                    time.sleep(3)
                else:
                    print(f"âš ï¸ Pagination bulunamadÄ± - tek sayfa varsayÄ±lÄ±yor")

            # Sayfa sayÄ±sÄ±nÄ± bul - en bÃ¼yÃ¼k sayÄ±yÄ± al
            max_page = 1
            for link in page_links:
                text = link.text.strip()

                # Sadece rakam olan linkleri kontrol et (1, 2, 3, ..., 421 gibi)
                # "..." gibi break-view'larÄ± atla
                if text.isdigit():
                    page_num = int(text)
                    if page_num > max_page:
                        max_page = page_num

            print(f"DEBUG: max_page = {max_page}")
            return max_page
            
        except Exception as e:
            logger.warning(f"Pagination detection failed: {e}")
            return 1
    
    def scrape_city(self, city: str, max_pages: int = None, api_mode: bool = False, progress_callback=None, stop_checker=None) -> List[Dict[str, Any]]:
        """Tek bir ÅŸehir iÃ§in tÃ¼m ilanlarÄ± tara"""
        self._log_location_start(city, self._build_location_url(city))

        # Durdurma denetleyicisini belirle
        _stop_checker = stop_checker or getattr(self, '_stop_checker', None)

        def is_stop_requested():
            if _stop_checker and _stop_checker():
                return True
            try:
                from api.status import task_status
                return task_status.is_stop_requested()
            except:
                return False

        if progress_callback:
            progress_callback(f"{city} iÃ§in tarama baÅŸlatÄ±lÄ±yor...", current=0, total=100)

        try:
            # Åehir seÃ§ (doÄŸrudan ÅŸehir URL'ine gider)
            if not self.select_single_city(city):
                task_log.line(f"âŒ {city} seÃ§ilemedi, atlanÄ±yor", level="error")
                return []

            # SÄ±fÄ±r sonuÃ§ kontrolÃ¼
            try:
                listing_count_elem = self.driver.find_elements(
                    By.CSS_SELECTOR, "span.applied-filters__count"
                )
                if listing_count_elem:
                    count_text = listing_count_elem[0].text.strip()
                    count_text_clean = count_text.replace('.', '')
                    import re
                    match = re.search(r'(\d+)', count_text_clean)
                    if match:
                        actual_count = int(match.group(1))
                        if actual_count == 0:
                            task_log.line(f"âš ï¸ {city} iÃ§in ilan bulunamadÄ±", level="warning")
                            return []
            except Exception:
                pass

            # Toplam sayfa sayÄ±sÄ±nÄ± al
            total_pages = self.get_total_pages()

            # Sayfa sayÄ±sÄ±nÄ± al (None = limit yok, tÃ¼m sayfalar)
            if api_mode:
                 if max_pages is not None:
                     pages_to_scrape = min(max_pages, total_pages)
                 else:
                     pages_to_scrape = total_pages
            else:
                if total_pages > 1:
                    try:
                        user_input = input(f"{city} iÃ§in kaÃ§ sayfa taranacak? (1-{total_pages}): ").strip()
                        pages_to_scrape = min(int(user_input), total_pages)
                        if pages_to_scrape < 1:
                            pages_to_scrape = 1
                    except ValueError:
                        pages_to_scrape = min(3, total_pages)
                        print(f"GeÃ§ersiz giriÅŸ, varsayÄ±lan {pages_to_scrape} sayfa kullanÄ±lÄ±yor.")
                else:
                    pages_to_scrape = 1

            self._log_location_plan(city, pages_to_scrape)

            city_listings = []
            total_new_listings = 0  # Sadece yeni eklenen ilan sayÄ±sÄ±

            # SayfalarÄ± tara
            for page in range(1, pages_to_scrape + 1):
                # Durdurma kontrolÃ¼ - her sayfa baÅŸÄ±nda kontrol et
                if is_stop_requested():
                    task_log.line(f"âš ï¸ Durdurma isteÄŸi alÄ±ndÄ±! {total_new_listings} yeni ilan kaydediliyor...", level="warning")
                    break

                self._log_page_start(city, page, pages_to_scrape)

                if progress_callback:
                    # Ä°lerleme: tamamlanan sayfa sayÄ±sÄ± Ã¼zerinden hesapla
                    # Sayfa 5 taranmaya baÅŸladÄ±ÄŸÄ±nda 4 tamamlanmÄ±ÅŸ = %80
                    completed_pages = page - 1
                    page_progress = int((completed_pages / pages_to_scrape) * 100)
                    progress_callback(f"{city} - Sayfa {page}/{pages_to_scrape} taranÄ±yor...", current=page, total=pages_to_scrape, progress=page_progress)

                page_url = self.driver.current_url.split('?')[0]
                if page > 1:
                    # Åehir URL'ini kullan (base_url deÄŸil!)
                    page_url = f"{page_url}?page={page}"
                    self.driver.get(page_url)
                    self.random_long_wait()  # Gizli mod: sayfa geÃ§iÅŸi
                    
                # SonuÃ§larÄ± bekle - timeout hatalarÄ±nÄ± takip et
                result_element = self.wait_for_element(self.common_selectors.get("listing_results"))
                
                if result_element is None:
                    # Zaman aÅŸÄ±mÄ± - sayfa yÃ¼klenemedi, baÅŸarÄ±sÄ±z sayfa olarak kaydet
                    task_log.line(f"   âš ï¸ Sayfa {page} yÃ¼klenemedi - retry listesine eklendi", level="warning")
                    failed_pages_tracker.add_failed_page(FailedPageInfo(
                        url=page_url if page > 1 else self.driver.current_url,
                        page_number=page,
                        city=city,
                        district=None,
                        error="Timeout waiting for listing results",
                        max_pages=pages_to_scrape,
                        listing_type=self.listing_type,
                        category=self.current_category,
                        subtype_path=self.subtype_path
                    ))
                    continue

                page_listings = self.scrape_current_page(fallback_city=city)

                # 0 ilan bulunduysa ve bu beklenmiyorsa baÅŸarÄ±sÄ±z sayfa olarak iÅŸaretle
                if len(page_listings) == 0 and page > 1:
                    task_log.line(f"   âš ï¸ Sayfa {page}'de 0 ilan - retry listesine eklendi", level="warning")
                    failed_pages_tracker.add_failed_page(FailedPageInfo(
                        url=page_url,
                        page_number=page,
                        city=city,
                        district=None,
                        error="0 listings found on page",
                        max_pages=pages_to_scrape,
                        listing_type=self.listing_type,
                        category=self.current_category,
                        subtype_path=self.subtype_path
                    ))
                else:
                    city_listings.extend(page_listings)

                    # Her sayfa sonrasÄ± DB'ye anÄ±nda kaydet
                    new_c = updated_c = unchanged_c = 0
                    if page_listings and self.db:
                        new_c, updated_c, unchanged_c = save_listings_to_db(
                            self.db,
                            page_listings,
                            platform="hepsiemlak",
                            kategori=self.category,
                            ilan_tipi=self.listing_type,
                            alt_kategori=self.subtype_name,
                            scrape_session_id=self.scrape_session_id
                        )
                        total_new_listings += new_c  # Yeni eklenenleri say
                        self.total_new_listings += new_c
                    self._log_page_result(page, len(page_listings), new_c, updated_c, unchanged_c)

                if page < pages_to_scrape:
                    self.random_medium_wait()  # Gizli mod: sayfalar arasÄ±

            self._log_location_complete(city, len(city_listings))
            return city_listings

        except Exception as e:
            task_log.line(f"âŒ {city} tarama hatasÄ±: {e}", level="error")
            return []

    def scrape_city_with_districts(self, city: str, districts: List[str], max_pages: int = None, progress_callback=None, stop_checker=None) -> Dict[str, List[Dict[str, Any]]]:
        """Bir ÅŸehir iÃ§in belirtilen ilÃ§eleri ayrÄ± ayrÄ± tara ve kaydet"""
        all_results = {}  # Ä°lÃ§e -> Ä°lanlar mapping
        total_new_listings = 0  # Sadece yeni eklenen ilan sayÄ±sÄ±

        # Durdurma denetleyicisini belirle
        _stop_checker = stop_checker or getattr(self, '_stop_checker', None)

        def is_stop_requested():
            if _stop_checker and _stop_checker():
                return True
            try:
                from api.status import task_status
                return task_status.is_stop_requested()
            except:
                return False

        task_log.section(
            f"ğŸ“ TaranÄ±yor: {city}",
            "ğŸ¯ Ä°lÃ§e filtreli tarama",
            "ğŸ§­ YÃ¶ntem: selenium",
        )

        # Ä°lÃ§e seÃ§imi yoksa tÃ¼m ÅŸehri scrape et
        if not districts or len(districts) == 0:
            task_log.line(f"{city}: tÃ¼m ilÃ§eler taranÄ±yor")
            # Åehir bazlÄ± kayÄ±t iÃ§in eski formatta dÃ¶ndÃ¼r
            city_listings = self.scrape_city(city, max_pages, api_mode=True, progress_callback=progress_callback, stop_checker=_stop_checker)
            return {city: city_listings}

        task_log.line(f"ğŸ“‹ SeÃ§ili ilÃ§eler: {', '.join(districts)}")
        task_log.line(f"ğŸ¯ {city} - {len(districts)} ilÃ§e ayrÄ± ayrÄ± taranacak")

        # Ã–nce dropdown'dan gerÃ§ek URL'leri al
        task_log.line(f"ğŸ” {city} iÃ§in ilÃ§e URL'leri alÄ±nÄ±yor...")
        district_url_map = self.get_district_urls_from_dropdown(city)

        if not district_url_map:
            task_log.line(f"âš ï¸ {city} iÃ§in ilÃ§e URL'leri alÄ±namadÄ±, manuel URL oluÅŸturulacak", level="warning")

        # Her ilÃ§eyi ayrÄ± ayrÄ± tara
        for idx, district in enumerate(districts, 1):
            # Durdurma kontrolÃ¼ - her ilÃ§e baÅŸÄ±nda kontrol et
            if is_stop_requested():
                task_log.line(f"âš ï¸ Durdurma isteÄŸi alÄ±ndÄ±! {len(all_results)} ilÃ§e kaydedildi.", level="warning")
                break

            district_listings = []  # Bu ilÃ§enin ilanlarÄ±

            try:
                # GerÃ§ek URL varsa onu kullan, yoksa manuel oluÅŸtur
                real_url = district_url_map.get(district)
                location_url = real_url or self._build_location_url(district)
                if location_url.startswith('/'):
                    location_url = f"https://www.hepsiemlak.com{location_url}"
                self._log_location_start(f"{city} / {district}", location_url)

                if real_url:
                    # GÃ¶receli URL'yi tam URL'ye Ã§evir
                    if real_url.startswith('/'):
                        real_url = f"https://www.hepsiemlak.com{real_url}"
                    self.driver.get(real_url)
                    time.sleep(5)

                    # URL doÄŸru mu kontrol et
                    if district.lower().replace(' ', '-') in self.driver.current_url.lower() or \
                       self._normalize_text(district) in self.driver.current_url.lower():
                        pass
                    else:
                        task_log.line(f"âš ï¸ {district} - URL redirect olmuÅŸ olabilir: {self.driver.current_url}", level="warning")
                else:
                    # Yedek: Manuel URL oluÅŸtur
                    if not self.select_single_district(district):
                        task_log.line(f"âš ï¸ {district} ilÃ§esi yÃ¼klenemedi, atlanÄ±yor", level="warning")
                        continue

                # SÄ±fÄ±r sonuÃ§ kontrolÃ¼ - daha gÃ¼venilir kontrol
                try:
                    # Ã–nce gerÃ§ek ilan sayÄ±sÄ±nÄ± kontrol et
                    listing_count_elem = self.driver.find_elements(
                        By.CSS_SELECTOR, "span.applied-filters__count"
                    )
                    if listing_count_elem:
                        count_text = listing_count_elem[0].text.strip()
                        # "iÃ§in 0 ilan" veya "0 ilan bulundu" kontrolÃ¼
                        count_text_clean = count_text.replace('.', '')
                        import re
                        match = re.search(r'(\d+)', count_text_clean)
                        if match:
                            actual_count = int(match.group(1))
                            if actual_count == 0:
                                task_log.line(f"âš ï¸ {district} iÃ§in ilan bulunamadÄ±", level="warning")
                                continue
                except Exception as e:
                    logger.debug(f"Ä°lan sayÄ±sÄ± kontrolÃ¼ hatasÄ±: {e}")

                # Toplam sayfa sayÄ±sÄ±nÄ± al
                total_pages = self.get_total_pages()

                pages_to_scrape = min(max_pages, total_pages) if max_pages is not None else total_pages
                self._log_location_plan(f"{city} / {district}", pages_to_scrape)

                # Bu ilÃ§e iÃ§in sayfalarÄ± tara
                for page in range(1, pages_to_scrape + 1):
                    # Durdurma kontrolÃ¼ - her sayfa baÅŸÄ±nda kontrol et
                    if is_stop_requested():
                        task_log.line(f"âš ï¸ Durdurma isteÄŸi alÄ±ndÄ±! {district} iÃ§in {len(district_listings)} ilan kaydediliyor...", level="warning")
                        # Mevcut ilÃ§e verilerini kaydet
                        if district_listings:
                            all_results[district] = district_listings
                            self._save_district_data(city, district, district_listings)
                        break

                    self._log_page_start(f"{city} / {district}", page, pages_to_scrape)

                    if progress_callback:
                        # Ä°lerleme: ilÃ§e ve sayfa bilgisini birlikte gÃ¶ster
                        overall_progress = int(((idx - 1 + (page / pages_to_scrape)) / len(districts)) * 100)
                        progress_callback(
                            f"{district} - Sayfa {page}/{pages_to_scrape}",
                            current=idx,
                            total=len(districts),
                            progress=overall_progress
                        )

                    page_url = self.driver.current_url.split('?')[0]
                    if page > 1:
                        page_url = f"{page_url}?page={page}"
                        self.driver.get(page_url)
                        self.random_long_wait()
                    
                    # SonuÃ§larÄ± bekle - timeout hatalarÄ±nÄ± takip et
                    result_element = self.wait_for_element(self.common_selectors.get("listing_results"))
                    
                    if result_element is None:
                        # Zaman aÅŸÄ±mÄ± - sayfa yÃ¼klenemedi, baÅŸarÄ±sÄ±z sayfa olarak kaydet
                        task_log.line(f"   âš ï¸ Sayfa {page} yÃ¼klenemedi - retry listesine eklendi", level="warning")
                        failed_pages_tracker.add_failed_page(FailedPageInfo(
                            url=page_url if page > 1 else self.driver.current_url,
                            page_number=page,
                            city=city,
                            district=district,
                            error="Timeout waiting for listing results",
                            max_pages=pages_to_scrape,
                            listing_type=self.listing_type,
                            category=self.current_category,
                            subtype_path=self.subtype_path
                        ))
                        continue

                    page_listings = self.scrape_current_page(fallback_city=city, fallback_district=district)

                    # 0 ilan bulunduysa ve bu beklenmiyorsa baÅŸarÄ±sÄ±z sayfa olarak iÅŸaretle
                    if len(page_listings) == 0 and page > 1:
                        task_log.line(f"   âš ï¸ Sayfa {page}'de 0 ilan - retry listesine eklendi", level="warning")
                        failed_pages_tracker.add_failed_page(FailedPageInfo(
                            url=page_url,
                            page_number=page,
                            city=city,
                            district=district,
                            error="0 listings found on page",
                            max_pages=pages_to_scrape,
                            listing_type=self.listing_type,
                            category=self.current_category,
                            subtype_path=self.subtype_path
                        ))
                    else:
                        district_listings.extend(page_listings)

                        # Her sayfa sonrasÄ± DB'ye anÄ±nda kaydet
                        new_c = updated_c = unchanged_c = 0
                        if page_listings and self.db:
                            new_c, updated_c, unchanged_c = save_listings_to_db(
                                self.db,
                                page_listings,
                                platform="hepsiemlak",
                                kategori=self.category,
                                ilan_tipi=self.listing_type,
                                alt_kategori=self.subtype_name,
                                scrape_session_id=self.scrape_session_id
                            )
                            total_new_listings += new_c  # Yeni eklenenleri say
                            self.total_new_listings += new_c
                        self._log_page_result(page, len(page_listings), new_c, updated_c, unchanged_c)

                    if page < pages_to_scrape:
                        self.random_medium_wait()

                # Ä°lÃ§e verilerini kaydet
                if district_listings:
                    all_results[district] = district_listings
                    self._log_location_complete(f"{city} / {district}", len(district_listings))

                    # Her ilÃ§eyi hemen kaydet (bellek tasarrufu ve gÃ¼venlik iÃ§in)
                    self._save_district_data(city, district, district_listings)
                else:
                    task_log.line(f"âš ï¸ {district} - Ä°lan bulunamadÄ±", level="warning")

                # Ä°lÃ§eler arasÄ± bekleme
                if idx < len(districts):
                    self.random_medium_wait()

            except Exception as e:
                task_log.line(f"âŒ {district} tarama hatasÄ±: {e}", level="error")
                continue

        total_listings = sum(len(listings) for listings in all_results.values())
        task_log.section(
            f"âœ… {city} - TÃœM Ä°LÃ‡ELER TAMAMLANDI",
            f"Toplam Ä°lan SayÄ±sÄ±: {total_listings}",
            f"Taranan Ä°lÃ§e SayÄ±sÄ±: {len(all_results)}",
        )
        return all_results

    def _save_district_data(self, city: str, district: str, listings: List[Dict[str, Any]]):
        """Ä°lÃ§e istatistiklerini gÃ¼ncelle (DB kaydetme sayfa bazlÄ± yapÄ±lÄ±yor)"""
        if not listings:
            return
        # Not: Bu fonksiyon artÄ±k kullanÄ±lmÄ±yor, yeni ilan sayÄ±sÄ± callback iÃ§inde hesaplanÄ±yor
        task_log.line(f"âœ… {city}/{district} - {len(listings)} ilan iÅŸlendi")

    def scrape_current_page(self, fallback_city: str = None, fallback_district: str = None) -> List[Dict[str, Any]]:
        """Mevcut sayfadaki tÃ¼m ilanlarÄ± tara; lokasyon bulunamazsa fallback_city ve fallback_district kullanÄ±lÄ±r"""
        listings = []

        try:
            container_sel = self.common_selectors.get("listing_container")
            self.wait_for_element(self.common_selectors.get("listing_results"))

            elements = self.driver.find_elements(By.CSS_SELECTOR, container_sel)

            for element in elements:
                try:
                    data = self.parser.extract_listing_data(element)
                    if data:
                        # Yedek: Lokasyon parse edilemezse, taranan ÅŸehir/ilÃ§eyi kullan
                        if fallback_city and (not data.get('il') or data.get('il') == 'BelirtilmemiÅŸ'):
                            data['il'] = fallback_city
                        if fallback_district and (not data.get('ilce') or data.get('ilce') == 'BelirtilmemiÅŸ'):
                            data['ilce'] = fallback_district
                        listings.append(data)
                    time.sleep(random.uniform(0.02, 0.08))  # Gizli mod
                except Exception as e:
                    continue

        except Exception as e:
            task_log.line(f"âŒ Sayfa tarama hatasÄ±: {e}", level="error")

        return listings
    
    def start_scraping_api(self, max_pages: int = 1, progress_callback=None, stop_checker=None):
        """API tarama giriÅŸ noktasÄ±; max_pages, progress_callback ve stop_checker parametreleri alÄ±r"""
        task_log.line(f"API: HepsiEmlak {self.listing_type.capitalize()} {self.category.capitalize()} Scraper (selenium)")

        # Durdurma denetleyicisini iÃ§ metotlarda kullanmak iÃ§in sakla
        self._stop_checker = stop_checker

        def is_stop_requested():
            """Durdurma isteÄŸini kontrol et - hem Celery hem bellek iÃ§i destekler"""
            if stop_checker and stop_checker():
                return True
            # Celery dÄ±ÅŸÄ± Ã§aÄŸrÄ±lar iÃ§in bellek iÃ§i duruma geri dÃ¶n
            try:
                from api.status import task_status
                return task_status.is_stop_requested()
            except:
                return False

        try:
            if not self.selected_cities:
                 task_log.line("No cities provided for API scrape", level="error")
                 return

            # Her ÅŸehri tara
            all_results = {}
            total_listings_count = 0
            total_cities = len(self.selected_cities)

            stopped_early = False  # Erken durdurulup durdurulmadÄ±ÄŸÄ±nÄ± takip et

            for city_idx, city in enumerate(self.selected_cities, 1):
                # Durdurma kontrolÃ¼ - kullanÄ±cÄ± durdur dediyse mevcut verileri kaydet
                if is_stop_requested():
                    task_log.line(f"âš ï¸ Durdurma isteÄŸi alÄ±ndÄ±! {len(all_results)} ÅŸehir tarandÄ±.", level="warning")
                    stopped_early = True
                    break

                # Toplam ilerleme hesabÄ± iÃ§in sarmalayÄ±cÄ± callback
                # city_idx ve total_cities'i closure'a alÄ±yoruz
                # progress_callback varsa (Celery) onu kullan, yoksa task_status'u dene
                def make_city_progress_callback(current_city_idx, num_cities, city_name):
                    def city_progress_callback(msg, current=None, total=None, progress=None):
                        # Åehir iÃ§i progress'i toplam progress'e Ã§evir
                        city_local_progress = progress if progress is not None else 0
                        overall = int(((current_city_idx - 1 + city_local_progress / 100) / num_cities) * 100)
                        if progress_callback:
                            progress_callback(
                                f"[{current_city_idx}/{num_cities}] {city_name}: {msg}",
                                current=current,
                                total=total,
                                progress=overall
                            )
                        else:
                            # Bellek iÃ§i task_status'a geri dÃ¶n
                            try:
                                from api.status import task_status
                                task_status.update(
                                    message=f"[{current_city_idx}/{num_cities}] {city_name}: {msg}",
                                    progress=overall,
                                    current=current,
                                    total=total
                                )
                            except:
                                pass
                    return city_progress_callback

                city_callback = make_city_progress_callback(city_idx, total_cities, city)

                # Ä°lÃ§e filtreleme var mÄ± kontrol et
                if self.selected_districts and city in self.selected_districts:
                    districts = self.selected_districts[city]
                    task_log.line(f"ğŸ¯ {city} iÃ§in ilÃ§e filtresi aktif: {len(districts)} ilÃ§e")
                    task_log.line(f"ğŸ“ Ä°lÃ§eler: {', '.join(districts)}")

                    # scrape_city_with_districts artÄ±k Dict[district -> listings] dÃ¶ndÃ¼rÃ¼yor
                    # VE her ilÃ§eyi otomatik olarak kaydediyor
                    district_results = self.scrape_city_with_districts(
                        city,
                        districts=districts,
                        max_pages=max_pages,
                        progress_callback=city_callback
                    )

                    # Sadece istatistik iÃ§in tutuyoruz (zaten kaydedildi)
                    if district_results:
                        all_results[city] = district_results
                        total_listings_count += sum(len(listings) for listings in district_results.values())
                else:
                    # Ä°lÃ§e seÃ§imi yoksa tÃ¼m ÅŸehri tara ve kaydet
                    task_log.line(f"ğŸ“ {city} - TÃ¼m ilÃ§eler taranacak (filtre yok)")
                    city_listings = self.scrape_city(
                        city,
                        max_pages=max_pages,
                        api_mode=True,
                        progress_callback=city_callback
                    )

                    if city_listings:
                        all_results[city] = city_listings
                        total_listings_count += len(city_listings)
                        self.total_scraped_count += len(city_listings)
                        # DB kaydetme scrape_city iÃ§inde sayfa bazlÄ± yapÄ±lÄ±yor

                self.random_medium_wait()  # Gizli mod: ÅŸehirler arasÄ±

            # Ã–zet bilgi (veriler zaten kaydedildi)
            if all_results:
                total = total_listings_count
                self._log_final_summary(stopped_early, len(all_results), total)
            else:
                self._log_final_summary(stopped_early, 0, 0)

            # ============================================================
            # RETRY MEKANÄ°ZMASI - BaÅŸarÄ±sÄ±z sayfalarÄ± yeniden dene
            # ============================================================
            max_retries = 3
            retry_round = 0
            successful_retries = 0

            while failed_pages_tracker.has_failed_pages() and retry_round < max_retries:
                retry_round += 1
                failed_pages = failed_pages_tracker.get_unretried(max_retry_count=max_retries)

                if not failed_pages:
                    break

                self._log_retry_round(retry_round, max_retries, len(failed_pages))

                # Ä°lerleme callback ile durumu gÃ¼ncelle
                if progress_callback:
                    progress_callback(
                        f"ğŸ”„ Retry #{retry_round} - {len(failed_pages)} sayfa",
                        current=0,
                        total=len(failed_pages),
                        progress=0
                    )

                # Her baÅŸarÄ±sÄ±z sayfa iÃ§in yeni tarayÄ±cÄ± ile dene
                for idx, page_info in enumerate(failed_pages, 1):
                    # Durdurma kontrolÃ¼
                    if is_stop_requested():
                        task_log.line("âš ï¸ Retry durduruldu!", level="warning")
                        break

                    task_log.line(f"ğŸ”„ [{idx}/{len(failed_pages)}] {page_info.city}/{page_info.district or 'tÃ¼m'} - Sayfa {page_info.page_number}")

                    if progress_callback:
                        progress_callback(
                            f"ğŸ”„ Retry #{retry_round}: {page_info.city} Sayfa {page_info.page_number}",
                            current=idx,
                            total=len(failed_pages),
                            progress=int((idx / len(failed_pages)) * 100)
                        )
                    
                    try:
                        # Yeni tarayÄ±cÄ± oturumu aÃ§
                        retry_manager = DriverManager()
                        retry_driver = retry_manager.start()
                        
                        try:
                            # DoÄŸrudan URL'e git
                            task_log.line(f"   ğŸŒ {page_info.url}")
                            retry_driver.get(page_info.url)
                            time.sleep(5)  # Sayfa yÃ¼klensin
                            
                            # SonuÃ§larÄ± bekle
                            from selenium.webdriver.support.ui import WebDriverWait
                            from selenium.webdriver.support import expected_conditions as EC
                            
                            wait = WebDriverWait(retry_driver, 30)
                            try:
                                wait.until(EC.presence_of_element_located(
                                    (By.CSS_SELECTOR, self.common_selectors.get("listing_results"))
                                ))
                                
                                # Ä°lanlarÄ± tara
                                container_sel = self.common_selectors.get("listing_container")
                                elements = retry_driver.find_elements(By.CSS_SELECTOR, container_sel)
                                
                                if elements:
                                    listings = []
                                    for element in elements:
                                        try:
                                            data = self.parser.extract_listing_data(element)
                                            if data:
                                                listings.append(data)
                                        except:
                                            continue
                                    
                                    if listings:
                                        task_log.line(f"   âœ… {len(listings)} ilan bulundu!")
                                        
                                        # Verileri kaydet
                                        if page_info.district:
                                            self._save_district_data(page_info.city, page_info.district, listings)
                                        else:
                                            if self.db:
                                                save_listings_to_db(
                                                    self.db,
                                                    listings,
                                                    platform="hepsiemlak",
                                                    kategori=self.category,
                                                    ilan_tipi=self.listing_type,
                                                    alt_kategori=self.subtype_name,
                                                    scrape_session_id=self.scrape_session_id
                                                )
                                        
                                        # BaÅŸarÄ±lÄ± olarak iÅŸaretle
                                        failed_pages_tracker.mark_as_success(
                                            page_info.city,
                                            page_info.district,
                                            page_info.page_number
                                        )
                                        successful_retries += 1
                                    else:
                                        task_log.line("   âš ï¸ 0 ilan - devam ediliyor", level="warning")
                                        failed_pages_tracker.increment_retry_count(
                                            page_info.city, 
                                            page_info.district, 
                                            page_info.page_number
                                        )
                                else:
                                    task_log.line("   âš ï¸ Element bulunamadÄ±", level="warning")
                                    failed_pages_tracker.increment_retry_count(
                                        page_info.city, 
                                        page_info.district, 
                                        page_info.page_number
                                    )
                                    
                            except Exception as timeout_e:
                                task_log.line(f"   âŒ Timeout: {timeout_e}", level="warning")
                                failed_pages_tracker.increment_retry_count(
                                    page_info.city, 
                                    page_info.district, 
                                    page_info.page_number
                                )
                                
                        finally:
                            # TarayÄ±cÄ±yÄ± kapat
                            retry_manager.stop()
                            
                    except Exception as e:
                        task_log.line(f"Retry hatasÄ±: {e}", level="error")
                        failed_pages_tracker.increment_retry_count(
                            page_info.city, 
                            page_info.district, 
                            page_info.page_number
                        )
                    
                    # Sayfalar arasÄ± kÄ±sa bekleme
                    time.sleep(random.uniform(1, 2))

            # Son Ã¶zet
            summary = failed_pages_tracker.get_summary()
            if summary["failed_count"] > 0 or successful_retries > 0:
                self._log_retry_summary(successful_retries, summary['failed_count'])
                
                if summary["failed_count"] > 0:
                    task_log.line(f"âš ï¸ {summary['failed_count']} sayfa retry sonrasÄ± hala baÅŸarÄ±sÄ±z", level="warning")
                    for fp in summary["failed_pages"]:
                        task_log.line(f"   - {fp['city']}/{fp['district'] or 'tÃ¼m'} Sayfa {fp['page_number']}: {fp['error']}", level="warning")

            return all_results

        except Exception as e:
            task_log.line(f"âŒ API tarama hatasÄ±: {e}", level="error")
            raise e


