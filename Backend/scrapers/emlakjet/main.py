# -*- coding: utf-8 -*-
"""EmlakJet Ana Scraper - gizli mod"""

import time
import random
import re
import unicodedata
from typing import Dict, List, Any, Optional, Set
from urllib.parse import urlparse

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.remote.webdriver import WebDriver

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from core.base_scraper import BaseScraper
from core.driver_manager import DriverManager
from core.selectors import get_selectors, get_common_selectors
from core.config import get_emlakjet_config
from core.failed_pages_tracker import FailedPagesTracker, FailedPageInfo, failed_pages_tracker
from utils.logger import get_logger, TaskLogLayout

from .parsers import KonutParser, ArsaParser, IsyeriParser, TuristikTesisParser

logger = get_logger(__name__)
task_log = TaskLogLayout(logger)


def _normalize_emlakjet_slug(value: Optional[str]) -> str:
    """Normalize slug-like values for robust filter matching."""
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
    ascii_only = re.sub(r"-{2,}", "-", ascii_only).strip("-")
    return ascii_only


def _extract_emlakjet_primary_slug_from_url(listing_url: str) -> Optional[str]:
    """Extract first URL path segment used by Emlakjet for category/subtype."""
    if not listing_url:
        return None

    try:
        parsed = urlparse(listing_url)
        host = (parsed.netloc or "").lower()
        if host and "emlakjet.com" not in host:
            return None

        parts = [part for part in parsed.path.split("/") if part]
        if not parts:
            return None
        return _normalize_emlakjet_slug(parts[0])
    except Exception:
        return None


def _get_expected_emlakjet_primary_slugs(listing_type: str, category: str) -> Set[str]:
    """Build expected first-path slugs for a listing_type/category combo."""
    expected: Set[str] = set()
    cfg = get_emlakjet_config()
    category_map = cfg.categories.get(listing_type or "", {})
    category_path = str(category_map.get(category or "", "")).strip("/")
    if category_path:
        expected.add(_normalize_emlakjet_slug(category_path.split("/")[0]))

    try:
        from .subtype_fetcher import fetch_subtypes

        for subtype in fetch_subtypes(listing_type, category):
            subtype_path = str(subtype.get("path", "")).strip("/")
            subtype_id = _normalize_emlakjet_slug(str(subtype.get("id", "")))
            if subtype_path:
                expected.add(_normalize_emlakjet_slug(subtype_path.split("/")[0]))
            if subtype_id:
                expected.add(subtype_id)
                listing_prefix = _normalize_emlakjet_slug(listing_type)
                if listing_prefix:
                    expected.add(f"{listing_prefix}-{subtype_id}")
    except Exception:
        pass

    return {slug for slug in expected if slug}


def _get_disallowed_emlakjet_primary_slugs(listing_type: str, category: str) -> Set[str]:
    """Collect known primary slugs of other categories to avoid false positives."""
    disallowed: Set[str] = set()
    cfg = get_emlakjet_config()
    category_map = cfg.categories.get(listing_type or "", {})
    for cat_key, cat_path in category_map.items():
        if cat_key == category:
            continue
        path = str(cat_path or "").strip("/")
        if not path:
            continue
        disallowed.add(_normalize_emlakjet_slug(path.split("/")[0]))
    return disallowed


def _matches_emlakjet_filters(
    listing_url: str,
    listing_type: str,
    category: str,
    alt_kategori: Optional[str],
    expected_primary_slugs: Set[str],
    disallowed_primary_slugs: Set[str],
) -> bool:
    """URL based listing_type/category/subtype guard for Emlakjet."""
    extracted = _extract_emlakjet_primary_slug_from_url(listing_url)
    if extracted is None:
        return False

    selected_subtype = _normalize_emlakjet_slug(alt_kategori)
    if selected_subtype:
        return extracted == selected_subtype or extracted.endswith(f"-{selected_subtype}")

    if expected_primary_slugs and extracted in expected_primary_slugs:
        return True

    listing_prefix = _normalize_emlakjet_slug(listing_type)
    category_slug = _normalize_emlakjet_slug(category)

    # Konut has many subtype slugs (satilik-daire, satilik-villa, ...).
    if category_slug == "konut" and listing_prefix and extracted.startswith(f"{listing_prefix}-"):
        return extracted not in disallowed_primary_slugs

    if category_slug and category_slug in extracted:
        return True

    if disallowed_primary_slugs and extracted in disallowed_primary_slugs:
        return False

    return not expected_primary_slugs


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
    """Save listing rows with URL-level listing_type/category/subtype validation."""
    if not db:
        return 0, 0, 0

    try:
        from database import crud

        records_to_save = listings
        new_count = 0
        updated_count = 0
        unchanged_count = 0

        if platform == "emlakjet":
            expected_primary_slugs = _get_expected_emlakjet_primary_slugs(ilan_tipi, kategori)
            disallowed_primary_slugs = _get_disallowed_emlakjet_primary_slugs(ilan_tipi, kategori)
            filtered_records: List[Dict] = []
            filtered_out = 0

            for data in listings:
                listing_url = data.get("ilan_url") or data.get("ilan_linki")
                if _matches_emlakjet_filters(
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
            _, status = crud.upsert_listing(
                db,
                data=data,
                platform=platform,
                kategori=kategori,
                ilan_tipi=ilan_tipi,
                alt_kategori=alt_kategori,
                scrape_session_id=scrape_session_id,
            )
            if status == "created":
                new_count += 1
            elif status == "updated":
                updated_count += 1
            elif status == "unchanged":
                unchanged_count += 1

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


class EmlakJetScraper(BaseScraper):
    """EmlakJet platformu ana scraper sÄ±nÄ±fÄ±"""
    
    CATEGORY_PARSERS = {
        'konut': KonutParser,
        'arsa': ArsaParser,
        'isyeri': IsyeriParser,
        'turistik_tesis': TuristikTesisParser,
        'kat_karsiligi_arsa': ArsaParser,  # Arsa parser'Ä± kullanÄ±r
        'devren_isyeri': IsyeriParser,     # Ä°ÅŸyeri parser'Ä± kullanÄ±r
        'gunluk_kiralik': KonutParser,     # Konut parser'Ä± kullanÄ±r
    }
    
    def __init__(
        self,
        driver: WebDriver,
        base_url: str = "https://www.emlakjet.com",
        category: str = "konut",
        selected_locations: Optional[Dict] = None,
        listing_type: Optional[str] = None,  # satilik/kiralik
        subtype_path: Optional[str] = None  # Alt kategori URL path'i (Ã¶rn: /satilik-daire)
    ):
        super().__init__(driver, base_url, "emlakjet", category, selected_locations)

        self.emlakjet_config = get_emlakjet_config()
        self.listing_type = listing_type
        self.subtype_path = subtype_path
        self.total_new_listings = 0  # Global kÃ¼mÃ¼latif yeni ilan sayacÄ±
        # Uygun parser'Ä± baÅŸlat
        parser_class = self.CATEGORY_PARSERS.get(category, KonutParser)
        self.parser = parser_class()
    
    def extract_listing_data(self, container) -> Optional[Dict[str, Any]]:
        """Kategori parser'Ä± ile ilan verisini Ã§Ä±kar"""
        return self.parser.extract_listing_data(container)
    
    def parse_category_details(self, quick_info: str, title: str) -> Dict[str, Any]:
        """Kategori parser'Ä± ile detaylarÄ± parse et"""
        return self.parser.parse_category_details(quick_info, title)
    
    @property
    def subtype_name(self) -> Optional[str]:
        """Dosya adlandÄ±rma iÃ§in subtype_path'inden alt kategori adÄ±nÄ± Ã§Ä±kar"""
        if self.subtype_path:
            # /satilik-daire -> daire
            path_part = self.subtype_path.strip('/').split('-')
            if len(path_part) >= 2:
                return path_part[-1].replace('-', '_')
        return None
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

    def scrape_current_page(self) -> List[Dict[str, Any]]:
        """Mevcut sayfadaki tÃ¼m ilanlarÄ± tara"""
        from datetime import datetime
        print = logger.debug

        listings = []
        try:
            container_selector = self.common_selectors.get("listing_container")
            if not container_selector:
                task_log.line("No listing_container selector defined", level="error")
                return []

            containers = self.find_elements_safe(container_selector)

            # EmlakJet: "Benzer Ä°lanlar" bÃ¶lÃ¼mÃ¼ndeki kartlarÄ± hariÃ§ tut
            if containers:
                filtered = []
                for c in containers:
                    try:
                        is_similar = self.driver.execute_script(
                            "return arguments[0].closest('[class*=\"similarListing\"], [class*=\"similarlisting\"]') !== null;", c
                        )
                        if not is_similar:
                            filtered.append(c)
                    except Exception:
                        filtered.append(c)
                if len(filtered) < len(containers):
                    logger.debug(f"Filtered out {len(containers) - len(filtered)} 'Benzer Ä°lanlar' listings")
                containers = filtered

            for container in containers:
                try:
                    data = self.extract_listing_data(container)
                    if data:
                        data['tarih'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        listings.append(data)
                except Exception as e:
                    logger.debug(f"Ä°lan Ã§Ä±karma hatasÄ±: {e}")
                    continue

        except Exception as e:
            task_log.line(f"Sayfa tarama hatasÄ±: {e}", level="error")

        return listings

    def get_location_options(self, location_type: str, current_url: str) -> tuple:
        """Mevcut sayfadan lokasyon seÃ§eneklerini ve ilan sayÄ±sÄ±nÄ± al"""
        try:
            logger.info(f"Getting {location_type} options...")

            self.driver.get(current_url)
            self.random_long_wait()  # Gizli mod: lokasyon listesi

            # Sayfa zaten yÃ¼klÃ¼ â€” ilan sayÄ±sÄ±nÄ± da aynÄ± anda al
            listing_count = self._parse_listing_count()

            location_options = []
            location_selector = self.common_selectors.get("location_links")

            location_links = self.driver.find_elements(By.CSS_SELECTOR, location_selector)

            # Duplicate kontrolÃ¼ iÃ§in seen set
            seen_names = set()

            for link in location_links:
                try:
                    location_name = link.text.strip().split()[0]
                    location_url = link.get_attribute("href")

                    if location_name and location_url:
                        # Duplicate kontrolÃ¼
                        if location_name not in seen_names:
                            seen_names.add(location_name)
                            location_options.append({
                                'name': location_name,
                                'url': location_url
                            })
                        else:
                            logger.debug(f"Duplicate {location_type} skipped: {location_name}")
                except Exception:
                    continue

            # LokasyonlarÄ± 4 sÃ¼tunda gÃ¶ster
            if location_options:
                print(f"\n{'=' * 80}")
                print(f"{location_type.upper()} (Toplam ilan: {listing_count})")
                print("=" * 80)

                cols = 4
                col_width = 20
                for i in range(0, len(location_options), cols):
                    row = ""
                    for j in range(cols):
                        idx = i + j
                        if idx < len(location_options):
                            name = location_options[idx]['name'][:col_width - 4]
                            row += f"{idx + 1:2d}. {name:<{col_width - 4}}"
                    print(row)

                print(f"\nToplam {len(location_options)} {location_type.lower()} bulundu.")

            return location_options, listing_count

        except Exception as e:
            logger.error(f"Error getting {location_type} options: {e}")
            return [], 0

    def get_max_pages(self, target_url: Optional[str] = None) -> int:
        """URL iÃ§in binary search ile maksimum sayfa sayÄ±sÄ±nÄ± al"""
        try:
            if target_url:
                self.driver.get(target_url)
                self.random_medium_wait()  # Gizli mod

            # JavaScript ile yÃ¼kleme beklemesi iÃ§in explicit wait
            try:
                WebDriverWait(self.driver, 15).until(
                    lambda d: d.execute_script("return document.readyState") == "complete"
                )
                logger.debug("Page fully loaded (document ready)")
            except Exception as e:
                logger.debug(f"Timeout waiting for document ready: {e}")

            # Ekstra bekleme - pagination elementleri yÃ¼klenmesi iÃ§in
            time.sleep(2)

            # Sonraki ok (right arrow) var mÄ± kontrol et - eÄŸer yoksa son sayfadayÄ±z
            # EÄŸer varsa, son sayfaya git ve oradaki pagination'dan max page bul
            right_arrow = self.driver.find_elements(By.CSS_SELECTOR, "li.styles_rightArrow__Kn4kW a")
            pagination_links = self.driver.find_elements(By.XPATH, "//a[contains(@href, 'sayfa=')]")

            if not right_arrow or not pagination_links:
                # Pagination yok veya son sayfadayÄ±z
                return 1

            # Sonraki ok var - son sayfaya git
            # Son sayfaya gitmek iÃ§in bÃ¼yÃ¼k bir sayfa numarasÄ± dene (Ã¶rn: 1000)
            # Emlakjet otomatik olarak son sayfaya yÃ¶nlendirecek
            separator = '&' if '?' in target_url else '?'
            last_page_url = f"{target_url}{separator}sayfa=9999"

            print(f"ğŸ” Son sayfa aranÄ±yor...")
            self.driver.get(last_page_url)
            time.sleep(2)

            # Son sayfadaki pagination link'lerini al
            last_page_links = self.driver.find_elements(By.XPATH, "//a[contains(@href, 'sayfa=')]")

            if not last_page_links:
                # HÃ¢lÃ¢ pagination yok, 1 varsay
                return 1

            # Son sayfadan maksimum sayfa numarasÄ±nÄ± Ã§Ä±kar
            page_numbers = []
            for link in last_page_links:
                try:
                    href = link.get_attribute("href")
                    if "?sayfa=" in href:
                        page_num = int(href.split("?sayfa=")[1].split("&")[0])
                        page_numbers.append(page_num)
                except Exception as e:
                    logger.debug(f"Error parsing page number from link: {e}")

            max_page = max(page_numbers) if page_numbers else 1

            # SeÃ§ili sayfa (active page) daha bÃ¼yÃ¼kse onu kullan
            try:
                selected_page = self.driver.find_element(By.CSS_SELECTOR, "span.styles_selected__hilA_")
                selected_num = int(selected_page.text)
                if selected_num > max_page:
                    max_page = selected_num
            except:
                pass

            logger.info(f"Max pages found: {max_page}")
            return max_page

        except Exception as e:
            logger.error(f"Error getting max pages: {e}")
            return 1
    
    # Emlakjet sayfalama limiti: 50 sayfa x 30 ilan = 1500 ilan
    PAGINATION_LIMIT = 1500

    def _parse_listing_count(self) -> int:
        """Zaten yÃ¼klenmiÅŸ sayfadan ilan sayÄ±sÄ±nÄ± parse et"""
        try:
            # "uygun ilan bulunamadÄ±" kontrolÃ¼
            no_results = self.driver.find_elements(
                By.CSS_SELECTOR, "span.styles_adsCount__A1YW5"
            )
            for el in no_results:
                if "bulunamadÄ±" in el.text.lower():
                    return 0

            # Ä°lan sayÄ±sÄ±nÄ± Ã§ek
            count_element = self.driver.find_elements(
                By.CSS_SELECTOR, "span.styles_adsCount__A1YW5 strong.styles_strong__cw1jn"
            )
            if count_element:
                text = count_element[0].text.strip().replace('.', '').replace(',', '')
                return int(text) if text.isdigit() else 0

            # Alternatif seÃ§ici
            count_element = self.driver.find_elements(
                By.CSS_SELECTOR, "strong.styles_strong__cw1jn"
            )
            if count_element:
                text = count_element[0].text.strip().replace('.', '').replace(',', '')
                return int(text) if text.isdigit() else 0

            return 0
        except Exception:
            return 0

    def get_listing_count(self, url: str) -> int:
        """URL'ye giderek toplam ilan sayÄ±sÄ±nÄ± al"""
        try:
            self.driver.get(url)
            self.random_medium_wait()
            return self._parse_listing_count()
        except Exception:
            return 0
    
    def select_provinces(self, api_indices: Optional[List[int]] = None, provinces: Optional[List[Dict]] = None) -> List[Dict]:
        """Taranacak illeri seÃ§"""
        print(f"\nğŸ™ï¸  Ä°L SEÃ‡Ä°MÄ°")
        if provinces is None:
            provinces, _ = self.get_location_options("Ä°ller", self.base_url)
        if not provinces:
            print("âŒ Ä°l bulunamadÄ±!")
            return []

        if api_indices:
             selected = [provinces[i - 1] for i in api_indices if 0 < i <= len(provinces)]
             if selected:
                 print(f"\nâœ… API: {len(selected)} il seÃ§ildi")
                 return selected
             # GeÃ§ersiz indeksler iÃ§in yedek
             return []

        print("\nğŸ¯ Ã‡OKLU Ä°L SEÃ‡Ä°MÄ°")
        print("Birden fazla seÃ§im iÃ§in: 1,3,5 veya 1-5")

        while True:
            user_input = input(f"\nÄ°l numaralarÄ±nÄ± girin (1-{len(provinces)}): ").strip()
            if not user_input:
                print("âŒ BoÅŸ giriÅŸ!")
                continue

            selections = self._parse_selection_input(user_input, len(provinces))
            if selections:
                selected = [provinces[i - 1] for i in selections]
                print(f"\nâœ… {len(selected)} il seÃ§ildi:")
                for p in selected:
                    print(f"   - {p['name']}")
                return selected
            else:
                print("âŒ GeÃ§ersiz seÃ§im!")
    
    def select_districts_for_province(self, province: Dict, api_mode: bool = False, api_districts: Optional[List[str]] = None) -> tuple:
        """Belirli bir il iÃ§in ilÃ§eleri seÃ§"""
        print(f"\nğŸ˜ï¸  {province['name']} Ä°LÃ‡ELERÄ°")
        districts, _ = self.get_location_options("Ä°lÃ§eler", province['url'])

        if not districts:
            print(f"âŒ {province['name']} iÃ§in ilÃ§e bulunamadÄ±!")
            return ([province], False)  # Ä°lÃ§e yoksa ilin kendisini dÃ¶ndÃ¼r

        if api_mode:
            # API modunda, isimle belirtilen ilÃ§eler varsa eÅŸleÅŸtir
            if api_districts:
                selected = [d for d in districts if d['name'] in api_districts]
                if selected:
                    for d in selected:
                        d['il'] = province['name']
                    return (selected, True)
                return ([], False)

            # API modunda ilÃ§e belirtilmemiÅŸse tÃ¼mÃ¼nÃ¼ tara
            for d in districts:
                d['il'] = province['name']
            return (districts, True)

        print("\n1. TÃ¼m ilÃ§eleri tara (her ilÃ§e iÃ§in mahalle seÃ§)")
        print("2. TÃ¼m ili direkt tara (ilÃ§e/mahalle seÃ§imi yapma)")
        print("3. Belirli ilÃ§eleri seÃ§")
        print("4. Bu ili atla")

        choice = self.get_user_choice(4)

        if choice == 1:
            for d in districts:
                d['il'] = province['name']
            return (districts, True)
        elif choice == 2:
            return ([province], False)
        elif choice == 4:
            return ([], False)

        # Belirli ilÃ§eleri seÃ§
        print("\nğŸ¯ Ä°LÃ‡E SEÃ‡Ä°MÄ° (Ã¶rn: 1,3,5 veya 1-5)")
        user_input = input(f"Ä°lÃ§e numaralarÄ±nÄ± girin (1-{len(districts)}): ").strip()

        selections = self._parse_selection_input(user_input, len(districts))
        if selections:
            selected = [districts[i - 1] for i in selections]
            for d in selected:
                d['il'] = province['name']
            print(f"âœ… {len(selected)} ilÃ§e seÃ§ildi")
            return (selected, True)
        else:
            return ([province], False)
    
    def select_neighborhoods_for_district(self, district: Dict, api_mode: bool = False) -> List[Dict]:
        """Belirli bir ilÃ§e iÃ§in mahalleleri seÃ§"""
        province_name = district.get('il', '')
        district_name = district['name']

        print(f"\nğŸ¡ {province_name} / {district_name} MAHALLELERÄ°")
        neighborhoods, _ = self.get_location_options("Mahalleler", district['url'])

        if not neighborhoods:
            return [district]  # Mahalle yoksa ilÃ§enin kendisini dÃ¶ndÃ¼r

        if api_mode:
            for n in neighborhoods:
                n['il'] = province_name
                n['ilce'] = district_name
            return neighborhoods

        print("\n1. TÃ¼m mahalleleri tara")
        print("2. Mahalle seÃ§")
        print("3. Bu ilÃ§eyi atla")

        choice = self.get_user_choice(3)

        if choice == 1:
            return [district]
        elif choice == 3:
            return []

        # Belirli mahalleleri seÃ§
        print("\nğŸ¯ MAHALLE SEÃ‡Ä°MÄ° (Ã¶rn: 1,3,5 veya 1-5)")
        user_input = input(f"Mahalle numaralarÄ±nÄ± girin (1-{len(neighborhoods)}): ").strip()

        selections = self._parse_selection_input(user_input, len(neighborhoods))
        if selections:
            selected = [neighborhoods[i - 1] for i in selections]
            for n in selected:
                n['il'] = province_name
                n['ilce'] = district_name
            print(f"âœ… {len(selected)} mahalle seÃ§ildi")
            return selected
        else:
            return [district]
    
    def _is_stop_requested(self) -> bool:
        """Durdurma isteÄŸi olup olmadÄ±ÄŸÄ±nÄ± kontrol et"""
        return self._stop_checker is not None and self._stop_checker()

    def _is_listing_limit_reached(self) -> bool:
        """Maksimum ilan limitine ulaÅŸÄ±lÄ±p ulaÅŸÄ±lmadÄ±ÄŸÄ±nÄ± kontrol et"""
        return self._max_listings > 0 and len(self.all_listings) >= self._max_listings

    def _make_page_callback(self, prov_name: str, dist_name: str, tgt: Dict, page_num_ref: List[int], new_listings_count_ref: List[int]):
        """Her sayfa sonrasÄ± ilanlarÄ± DB'ye kaydetmek iÃ§in callback oluÅŸtur"""
        def _on_page_scraped(page_listings):
            for listing in page_listings:
                listing['il'] = prov_name
                if tgt['type'] == 'mahalle':
                    listing['ilce'] = dist_name
                    listing['mahalle'] = tgt['label'].split('/')[-1].strip()
                elif tgt['type'] == 'ilce':
                    listing['ilce'] = dist_name

            if self.db:
                new_count, updated_count, unchanged_count = save_listings_to_db(
                    self.db,
                    page_listings,
                    platform="emlakjet",
                    kategori=self.category,
                    ilan_tipi=self.listing_type,
                    alt_kategori=self.subtype_name,
                    scrape_session_id=self.scrape_session_id,
                    log_db_save=False,
                )
                page_num_ref[0] += 1
                new_listings_count_ref[0] += new_count  # Yeni eklenenleri say
                self._log_page_result(page_num_ref[0], len(page_listings), new_count, updated_count, unchanged_count)
        return _on_page_scraped

    def scrape_pages(self, target_url: str, max_pages: int, on_page_scraped=None,
                     location_label: str = "", province: str = "", district: str = "", new_listings_count_ref: List[int] = None) -> bool:
        """BaÅŸarÄ±sÄ±z sayfa takibi ile sayfa tarama"""
        print = task_log.line
        first_page_count = 0

        for current_page in range(1, max_pages + 1):
            if hasattr(self, '_stop_checker') and self._stop_checker and self._stop_checker():
                task_log.line("Durdurma isteÄŸi alÄ±ndÄ±, sayfa tarama sonlandÄ±rÄ±lÄ±yor", level="warning")
                break

            if hasattr(self, '_max_listings') and self._max_listings > 0 and len(self.all_listings) >= self._max_listings:
                task_log.line(f"Ä°lan limitine ulaÅŸÄ±ldÄ± ({self._max_listings}), sayfa tarama sonlandÄ±rÄ±lÄ±yor", level="warning")
                break

            self._log_page_start(location_label or province or district or "Lokasyon", current_page, max_pages)

            try:
                if current_page > 1:
                    separator = '&' if '?' in target_url else '?'
                    page_url = f"{target_url}{separator}sayfa={current_page}"
                else:
                    page_url = target_url

                self.driver.get(page_url)
                time.sleep(self.config.wait_between_pages)

                # SÄ±fÄ±r ilan kontrolÃ¼ (ilk sayfa)
                if current_page == 1:
                    try:
                        no_results = self.driver.find_elements(
                            By.CSS_SELECTOR, "span.styles_title__e_y3h"
                        )
                        for element in no_results:
                            if "ilan bulunamadÄ±" in element.text.lower():
                                task_log.line("âš ï¸ Bu lokasyonda ilan bulunamadÄ±, atlanÄ±yor...", level="warning")
                                return True
                    except:
                        pass

                listings = self.scrape_current_page()

                # 0 ilan bulunduysa ve ilk sayfa deÄŸilse â†’ failed page olarak kaydet
                if len(listings) == 0 and current_page > 1:
                    task_log.line(f"   âš ï¸ Sayfa {current_page}'de 0 ilan - retry listesine eklendi", level="warning")
                    failed_pages_tracker.add_failed_page(FailedPageInfo(
                        url=page_url,
                        page_number=current_page,
                        city=province,
                        district=district,
                        error="0 listings found on page",
                        max_pages=max_pages,
                        listing_type=self.listing_type or "",
                        category=self.category or "",
                        subtype_path=self.subtype_path
                    ))
                else:
                    self.all_listings.extend(listings)

                    # Sadece yeni eklenenleri saymak iÃ§in
                    if on_page_scraped and listings:
                        on_page_scraped(listings)
                    elif listings:
                        self._log_page_result(current_page, len(listings), 0, 0, 0)

                if current_page == 1:
                    first_page_count = len(listings)

            except Exception as e:
                task_log.line(f"Error scraping page {current_page}: {e}", level="error")
                task_log.line(f"   âš ï¸ Sayfa {current_page} yÃ¼klenemedi - retry listesine eklendi", level="warning")
                # Sayfa yÃ¼kleme hatasÄ± â†’ baÅŸarÄ±sÄ±z sayfa
                page_url = target_url if current_page == 1 else f"{target_url}{'&' if '?' in target_url else '?'}sayfa={current_page}"
                failed_pages_tracker.add_failed_page(FailedPageInfo(
                    url=page_url,
                    page_number=current_page,
                    city=province,
                    district=district,
                    error=str(e),
                    max_pages=max_pages,
                    listing_type=self.listing_type or "",
                    category=self.category or "",
                    subtype_path=self.subtype_path
                ))
                continue

        return first_page_count == 0 and max_pages == 1

    def _scrape_target(self, target: Dict, province_name: str, district_name: str) -> bool:
        """Tek bir hedefi (il/ilÃ§e/mahalle) tara"""
        print = task_log.line
        url_max_pages = self.get_max_pages(target['url'])
        self._log_location_start(target['label'], target['url'])
        self._log_location_plan(target['label'], url_max_pages)
        print(f"ğŸ“Š {url_max_pages} sayfa mevcut, tamamÄ± taranacak.")

        page_num_ref = [0]  # Callback iÃ§inde sayfa sayacÄ± iÃ§in deÄŸiÅŸtirilebilir referans
        new_listings_count_ref = [0]  # Yeni eklenen ilan sayacÄ±
        page_callback = self._make_page_callback(province_name, district_name, target, page_num_ref, new_listings_count_ref)
        should_skip = self.scrape_pages(
            target['url'], url_max_pages,
            on_page_scraped=page_callback,
            location_label=target['label'],
            province=province_name,
            district=district_name,
            new_listings_count_ref=new_listings_count_ref
        )
        # Global kÃ¼mÃ¼latif sayaÃ§a ekle
        self.total_new_listings += new_listings_count_ref[0]
        logger.warning(f"ğŸ“Š EmlakJet KÃ¼mÃ¼latif Toplam: {self.total_new_listings} ilan")
        if not should_skip:
            self._log_location_complete(target['label'], new_listings_count_ref[0])
        return should_skip, new_listings_count_ref[0]

    def start_scraping_api(self, cities: Optional[List[str]] = None, districts: Optional[Dict[str, List[str]]] = None, max_listings: int = 0, progress_callback=None, stop_checker=None):
        """Ä°ki katmanlÄ± optimizasyonla API tarama giriÅŸ noktasÄ±"""
        print = task_log.line
        self._stop_checker = stop_checker
        self._max_listings = max_listings

        subtype_info = f" ({self.subtype_name})" if self.subtype_name else ""
        limit_info = f" (limit: {max_listings} ilan)" if max_listings > 0 else " (limitsiz)"
        print(f"\nğŸš€ API: EmlakJet {self.listing_type.capitalize()} {self.category.capitalize()}{subtype_info} Scraper baÅŸlatÄ±lÄ±yor{limit_info}")

        if progress_callback:
            progress_callback(f"{self.category.capitalize()}{subtype_info} taramasÄ± baÅŸlatÄ±lÄ±yor...", 0, 100, 0)

        try:
            # subtype_path varsa onu kullan, yoksa base_url
            start_url = self.base_url
            if self.subtype_path:
                start_url = f"https://www.emlakjet.com{self.subtype_path}"
                print(f"ğŸ“‹ Alt kategori kullanÄ±lÄ±yor: {self.subtype_path}")

            print("Ä°l listesi alÄ±nÄ±yor...")
            all_provinces, _ = self.get_location_options("Ä°ller", start_url)

            # AdÄ±m 1: Ä°lleri seÃ§
            if cities:
                api_indices = []
                cities_lower = [c.lower() for c in cities]
                for idx, p in enumerate(all_provinces, 1):
                    if p['name'].lower() in cities_lower:
                        api_indices.append(idx)

                if not api_indices:
                    logger.error(f"Åehirler iÃ§in eÅŸleÅŸen il bulunamadÄ±: {cities}")
                    logger.info(f"Mevcut iller: {[p['name'] for p in all_provinces[:5]]}...")
                    return

                provinces = self.select_provinces(api_indices=api_indices, provinces=all_provinces)
            else:
                logger.error("API taramasÄ± iÃ§in ÅŸehir belirtilmedi")
                return

            # AdÄ±m 2: Her ili optimizasyonla iÅŸle
            stopped = False
            scrape_stats = {}  # {il_adÄ±: {ilÃ§e_adÄ±: ilan_sayÄ±sÄ±}} â€” Ã¶zet rapor iÃ§in
            for prov_idx, province in enumerate(provinces, 1):
                if self._is_stop_requested():
                    print(f"\nâš ï¸ Durdurma isteÄŸi alÄ±ndÄ±! {len(self.all_listings)} ilan toplandÄ±.")
                    logger.warning(f"âš ï¸ Tarama erken durduruldu: {len(self.all_listings)} ilan")
                    stopped = True
                    break
                if self._is_listing_limit_reached():
                    stopped = True
                    break

                # Ä°l sayfasÄ±na git ve ilan sayÄ±sÄ±nÄ± al (get_listing_count sayfayÄ± yÃ¼kler)
                province_count = self.get_listing_count(province['url'])

                print("\n" + "=" * 70)
                print(f"ğŸ™ï¸  Ä°L {prov_idx}/{len(provinces)}: {province['name']} (Toplam Ä°lan: {province_count})")
                print("=" * 70)

                if progress_callback:
                    base_progress = ((prov_idx - 1) / len(provinces)) * 100
                    progress_callback(f"Ä°ÅŸleniyor: {province['name']}...", prov_idx, len(provinces), base_progress)

                # â”€â”€ OPTÄ°MÄ°ZASYON: Ä°l seviyesi kontrol â”€â”€
                if province_count == 0:
                    print(f"â­ï¸  {province['name']} â†’ 0 ilan, il atlanÄ±yor.")
                    continue

                if province_count <= self.PAGINATION_LIMIT:
                    # Ä°l genelinde â‰¤1500 ilan â€” ilÃ§e/mahalleye inmeye gerek yok
                    print(f"âš¡ {province['name']} â†’ {province_count} ilan (â‰¤{self.PAGINATION_LIMIT}), il seviyesinden taranÄ±yor.")
                    target = {'url': province['url'], 'label': province['name'], 'type': 'il'}
                    print(f"\nğŸ“ TaranÄ±yor: {target['label']}")
                    should_skip, new_count = self._scrape_target(target, province['name'], province['name'])
                    if should_skip:
                        print("â­ï¸  Bu lokasyon atlandÄ±.")
                    else:
                        print(f"   ğŸ“¦ Toplam: {new_count} yeni ilan toplandÄ±")
                        scrape_stats[province['name']] = {'(il seviyesi)': new_count}

                    if progress_callback:
                        overall = (prov_idx / len(provinces)) * 100
                        progress_callback(
                            f"{province['name']} (il seviyesi)",
                            1, 1, min(int(overall), 99),
                        )
                    continue

                # Ä°l > 1500 ilan â€” ilÃ§elere iniyoruz
                print(f"ğŸ“Š {province['name']} â†’ {province_count} ilan (>{self.PAGINATION_LIMIT}), ilÃ§e seviyesine iniliyor...")

                # Ä°lÃ§e filtreleme var mÄ± kontrol et
                province_name = province['name']
                api_districts_for_province = None
                if districts and province_name in districts:
                    api_districts_for_province = districts[province_name]
                    logger.info(f"{province_name} iÃ§in ilÃ§e filtresi aktif: {api_districts_for_province}")

                # Ä°lÃ§e listesini al
                district_list, _ = self.get_location_options("Ä°lÃ§eler", province['url'])

                if not district_list:
                    print(f"â­ï¸  {province['name']} ilÃ§e bulunamadÄ±, atlanÄ±yor.")
                    continue

                # Ä°lÃ§e filtresi uygula
                if api_districts_for_province:
                    district_list = [d for d in district_list if d['name'] in api_districts_for_province]
                    if not district_list:
                        print(f"â­ï¸  {province['name']} iÃ§in eÅŸleÅŸen ilÃ§e bulunamadÄ±.")
                        continue

                for d in district_list:
                    d['il'] = province_name

                # Her ilÃ§eyi iÅŸle
                for dist_idx, district in enumerate(district_list, 1):
                    if self._is_stop_requested():
                        print(f"\nâš ï¸ Durdurma isteÄŸi alÄ±ndÄ±! {len(self.all_listings)} ilan toplandÄ±.")
                        logger.warning(f"âš ï¸ Tarama erken durduruldu: {len(self.all_listings)} ilan")
                        stopped = True
                        break
                    if self._is_listing_limit_reached():
                        stopped = True
                        break

                    # Ä°lÃ§e sayfasÄ±na git ve ilan sayÄ±sÄ±nÄ± al
                    district_count = self.get_listing_count(district['url'])

                    print(f"\nğŸ“ Ä°lÃ§e {dist_idx}/{len(district_list)}: {district['name']} (Ä°lan: {district_count})")

                    # â”€â”€ OPTÄ°MÄ°ZASYON: Ä°lÃ§e seviyesi kontrol â”€â”€
                    if district_count == 0:
                        print(f"â­ï¸  {district['name']} â†’ 0 ilan, ilÃ§e atlanÄ±yor.")
                        continue

                    if district_count <= self.PAGINATION_LIMIT:
                        # Ä°lÃ§ede â‰¤1500 ilan â€” mahalleye inmeye gerek yok
                        print(f"âš¡ {district['name']} â†’ {district_count} ilan (â‰¤{self.PAGINATION_LIMIT}), ilÃ§e seviyesinden taranÄ±yor.")
                        target = {
                            'url': district['url'],
                            'label': f"{province_name} / {district['name']}",
                            'type': 'ilce'
                        }
                        print(f"\nğŸ“ TaranÄ±yor: {target['label']}")
                        should_skip, new_count = self._scrape_target(target, province_name, district['name'])

                        if progress_callback:
                            province_base = ((prov_idx - 1) / len(provinces)) * 100
                            province_range = 100 / len(provinces)
                            district_range = province_range / max(len(district_list), 1)
                            overall = province_base + dist_idx * district_range
                            progress_callback(
                                f"{province_name} > {district['name']}",
                                dist_idx, len(district_list), min(int(overall), 99),
                            )

                        if should_skip:
                            print("â­ï¸  Bu lokasyon atlandÄ±.")
                        else:
                            print(f"   ğŸ“¦ Toplam: {new_count} yeni ilan toplandÄ±")
                            scrape_stats.setdefault(province_name, {})[district['name']] = new_count
                        continue

                    # Ä°lÃ§e > 1500 ilan â€” mahallelere iniyoruz
                    print(f"ğŸ“Š {district['name']} â†’ {district_count} ilan (>{self.PAGINATION_LIMIT}), mahalle seviyesine iniliyor...")

                    neighborhoods, _ = self.get_location_options("Mahalleler", district['url'])

                    if not neighborhoods:
                        # Mahalle bulunamadÄ± â€” ilÃ§e seviyesinden tara
                        target = {
                            'url': district['url'],
                            'label': f"{province_name} / {district['name']}",
                            'type': 'ilce'
                        }
                        print(f"\nğŸ“ Mahalle bulunamadÄ±, ilÃ§e seviyesinden taranÄ±yor: {target['label']}")
                        should_skip, new_count = self._scrape_target(target, province_name, district['name'])
                        if should_skip:
                            print("â­ï¸  Bu lokasyon atlandÄ±.")
                        else:
                            print(f"   ğŸ“¦ Toplam: {new_count} yeni ilan toplandÄ±")
                        continue

                    for n in neighborhoods:
                        n['il'] = province_name
                        n['ilce'] = district['name']

                    targets = [
                        {
                            'url': n['url'],
                            'label': f"{n.get('il', '')} / {n.get('ilce', '')} / {n['name']}",
                            'type': 'mahalle'
                        }
                        for n in neighborhoods
                    ]

                    total_targets = len(targets)
                    for target_idx, target in enumerate(targets, 1):
                        if self._is_stop_requested():
                            print(f"\nâš ï¸ Durdurma isteÄŸi alÄ±ndÄ±! {len(self.all_listings)} ilan toplandÄ±.")
                            logger.warning(f"âš ï¸ Tarama erken durduruldu: {len(self.all_listings)} ilan")
                            stopped = True
                            break
                        if self._is_listing_limit_reached():
                            stopped = True
                            break

                        print(f"\nğŸ“ TaranÄ±yor: {target['label']} ({target_idx}/{total_targets})")
                        should_skip, new_count = self._scrape_target(target, province_name, district['name'])

                        # Mahalle bazlÄ± istatistikler â€” ilÃ§e altÄ±nda topla
                        if new_count > 0:
                            scrape_stats.setdefault(province_name, {})
                            scrape_stats[province_name][district['name']] = scrape_stats[province_name].get(district['name'], 0) + new_count

                        if progress_callback:
                            province_base = ((prov_idx - 1) / len(provinces)) * 100
                            province_range = 100 / len(provinces)
                            district_range = province_range / max(len(district_list), 1)
                            target_range = district_range / max(total_targets, 1)
                            overall = province_base + (dist_idx - 1) * district_range + target_idx * target_range
                            progress_callback(
                                f"{province_name} > {district['name']} > {target['label'].split('/')[-1].strip()}",
                                target_idx, total_targets, min(int(overall), 99),
                            )

                        if should_skip:
                            print("â­ï¸  Bu lokasyon atlandÄ±.")
                        else:
                            print(f"   ğŸ“¦ Toplam: {new_count} yeni ilan toplandÄ±")

                    if stopped:
                        break
                if stopped:
                    break

            if self._is_listing_limit_reached():
                print(f"\nğŸ¯ Ä°lan limitine ulaÅŸÄ±ldÄ±: {len(self.all_listings)} / {self._max_listings}")

            # â”€â”€ HÄ°YERARÅÄ°K Ã–ZET RAPOR â”€â”€
            print(f"\n{'=' * 70}")
            if stopped and self._is_stop_requested():
                print("âš ï¸  ERKEN DURDURULDU")
                logger.warning(f"âš ï¸ Tarama erken durduruldu: {self.total_new_listings} yeni ilan")
            elif self.all_listings:
                print("âœ… TARAMA BAÅARIYLA TAMAMLANDI")
                logger.info(f"âœ… Tarama tamamlandÄ±: {self.total_new_listings} yeni ilan")
            else:
                print("âŒ HÄ°Ã‡ Ä°LAN BULUNAMADI")
                logger.warning("âš ï¸ HiÃ§ ilan bulunamadÄ±")

            if scrape_stats:
                print(f"ğŸ“Š Taranan Ä°l SayÄ±sÄ±: {len(scrape_stats)}")
                print(f"ğŸ“Š Toplam Yeni Ä°lan SayÄ±sÄ±: {self.total_new_listings}")
                for city, districts_data in scrape_stats.items():
                    city_total = sum(districts_data.values())
                    print(f"   â€¢ {city}: {city_total} ilan ({len(districts_data)} ilÃ§e/bÃ¶lge)")
                    for district_name, count in districts_data.items():
                        print(f"      - {district_name}: {count} ilan")
            print("=" * 70)

            # â”€â”€ RETRY MEKANÄ°ZMASI â”€â”€
            max_retries = 3
            retry_round = 0
            successful_retries = 0

            while failed_pages_tracker.has_failed_pages() and retry_round < max_retries:
                if self._is_stop_requested():
                    print(f"\nâš ï¸ Retry durduruldu!")
                    break

                retry_round += 1
                failed_pages = failed_pages_tracker.get_unretried(max_retry_count=max_retries)

                if not failed_pages:
                    break

                print(f"\n{'=' * 70}")
                print(f"ğŸ”„ YENÄ°DEN DENEME #{retry_round}/{max_retries}")
                print(f"ğŸ“Š {len(failed_pages)} baÅŸarÄ±sÄ±z sayfa tekrar taranacak")
                print("=" * 70)

                if progress_callback:
                    progress_callback(
                        f"ğŸ”„ Retry #{retry_round} - {len(failed_pages)} sayfa",
                        0, len(failed_pages), 0
                    )

                for idx, page_info in enumerate(failed_pages, 1):
                    if self._is_stop_requested():
                        print(f"\nâš ï¸ Retry durduruldu!")
                        break

                    print(f"\nğŸ”„ [{idx}/{len(failed_pages)}] {page_info.city}/{page_info.district or 'tÃ¼m'} - Sayfa {page_info.page_number}")

                    if progress_callback:
                        progress_callback(
                            f"ğŸ”„ Retry #{retry_round}: {page_info.city} Sayfa {page_info.page_number}",
                            idx, len(failed_pages), int((idx / len(failed_pages)) * 100)
                        )

                    try:
                        retry_manager = DriverManager()
                        retry_driver = retry_manager.start()

                        try:
                            print(f"   ğŸŒ {page_info.url}")
                            retry_driver.get(page_info.url)
                            time.sleep(self.config.wait_between_pages + 1)

                            # Ä°lanlarÄ± tara
                            container_selector = self.common_selectors.get("listing_container")
                            containers = retry_driver.find_elements(By.CSS_SELECTOR, container_selector)

                            if containers:
                                listings = []
                                for container in containers:
                                    try:
                                        data = self.extract_listing_data(container)
                                        if data:
                                            listings.append(data)
                                    except:
                                        continue

                                if listings:
                                    print(f"   âœ… {len(listings)} ilan bulundu!")
                                    self.all_listings.extend(listings)

                                    # DB'ye kaydet
                                    if self.db:
                                        save_listings_to_db(
                                            self.db,
                                            listings,
                                            platform="emlakjet",
                                            kategori=self.category,
                                            ilan_tipi=self.listing_type,
                                            alt_kategori=self.subtype_name,
                                            scrape_session_id=self.scrape_session_id,
                                            log_db_save=False,
                                        )

                                    failed_pages_tracker.mark_as_success(
                                        page_info.city, page_info.district, page_info.page_number
                                    )
                                    successful_retries += 1
                                else:
                                    print(f"   âš ï¸ 0 ilan - devam ediliyor")
                                    failed_pages_tracker.increment_retry_count(
                                        page_info.city, page_info.district, page_info.page_number
                                    )
                            else:
                                print(f"   âš ï¸ Element bulunamadÄ±")
                                failed_pages_tracker.increment_retry_count(
                                    page_info.city, page_info.district, page_info.page_number
                                )
                        finally:
                            retry_manager.stop()

                    except Exception as e:
                        logger.error(f"Retry hatasÄ±: {e}")
                        failed_pages_tracker.increment_retry_count(
                            page_info.city, page_info.district, page_info.page_number
                        )

                    time.sleep(random.uniform(1, 2))

            # Yeniden deneme Ã¶zeti
            summary = failed_pages_tracker.get_summary()
            if summary["failed_count"] > 0 or successful_retries > 0:
                print(f"\n{'=' * 70}")
                print("ğŸ“Š RETRY Ã–ZETÄ°")
                print(f"   âœ… BaÅŸarÄ±lÄ± retry: {successful_retries}")
                print(f"   âŒ Kalan baÅŸarÄ±sÄ±z: {summary['failed_count']}")
                print("=" * 70)

                if summary["failed_count"] > 0:
                    logger.warning(f"âš ï¸ {summary['failed_count']} sayfa retry sonrasÄ± hala baÅŸarÄ±sÄ±z")
                    for fp in summary["failed_pages"]:
                        logger.warning(f"   - {fp['city']}/{fp['district'] or 'tÃ¼m'} Sayfa {fp['page_number']}: {fp['error']}")

        except Exception as e:
            logger.error(f"API tarama hatasÄ±: {e}")
            raise e


