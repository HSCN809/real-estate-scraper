# -*- coding: utf-8 -*-
"""
EmlakJet Main Scraper - STEALTH MODE
Refactored with randomized delays to avoid bot detection
"""

import time
import random
import unicodedata
from typing import Dict, List, Any, Optional

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.remote.webdriver import WebDriver

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from core.base_scraper import BaseScraper
from core.driver_manager import DriverManager
from core.selectors import get_selectors, get_common_selectors
from core.config import get_emlakjet_config
from utils.logger import get_logger
from utils.data_exporter import DataExporter

from .parsers import KonutParser, ArsaParser, IsyeriParser, TuristikTesisParser

logger = get_logger(__name__)


class EmlakJetScraper(BaseScraper):
    """
    Main scraper for EmlakJet platform.
    Handles category selection, location navigation, and scraping.
    """
    
    CATEGORY_PARSERS = {
        'konut': KonutParser,
        'arsa': ArsaParser,
        'isyeri': IsyeriParser,
        'turistik_tesis': TuristikTesisParser,
        'kat_karsiligi_arsa': ArsaParser,  # Uses arsa parser
        'devren_isyeri': IsyeriParser,     # Uses isyeri parser
        'gunluk_kiralik': KonutParser,     # Uses konut parser
    }
    
    def __init__(
        self,
        driver: WebDriver,
        base_url: str = "https://www.emlakjet.com",
        category: str = "konut",
        selected_locations: Optional[Dict] = None,
        listing_type: Optional[str] = None,  # satilik/kiralik
        subtype_path: Optional[str] = None  # Alt kategori URL path'i (örn: /satilik-daire)
    ):
        super().__init__(driver, base_url, "emlakjet", category, selected_locations)

        self.emlakjet_config = get_emlakjet_config()
        self.listing_type = listing_type
        self.subtype_path = subtype_path

        # Alt kategori adını çıkar
        subtype_name = None
        if subtype_path:
            # /satilik-daire -> daire
            path_part = subtype_path.strip('/').split('-')
            if len(path_part) >= 2:
                subtype_name = path_part[-1].replace('-', '_')

        # Hiyerarşik klasör yapısı: Outputs/EmlakJet Output/{listing_type}/{category}/{subtype}/
        self.exporter = DataExporter(
            output_dir="Outputs/EmlakJet Output",
            listing_type=listing_type,
            category=category,
            subtype=subtype_name
        )

        # Initialize the appropriate parser
        parser_class = self.CATEGORY_PARSERS.get(category, KonutParser)
        self.parser = parser_class()
    
    def extract_listing_data(self, container) -> Optional[Dict[str, Any]]:
        """Use the category parser to extract listing data"""
        return self.parser.extract_listing_data(container)
    
    def parse_category_details(self, quick_info: str, title: str) -> Dict[str, Any]:
        """Use the category parser to parse details"""
        return self.parser.parse_category_details(quick_info, title)
    
    @property
    def subtype_name(self) -> Optional[str]:
        """Extract subtype name from subtype_path for file naming"""
        if self.subtype_path:
            # /satilik-daire -> daire
            path_part = self.subtype_path.strip('/').split('-')
            if len(path_part) >= 2:
                return path_part[-1].replace('-', '_')
        return None

    def get_file_prefix(self) -> str:
        """Generate file prefix with subtype if available"""
        if self.subtype_name:
            return f"emlakjet_{self.listing_type}_{self.category}_{self.subtype_name}"
        return f"emlakjet_{self.listing_type}_{self.category}"

    def get_location_options(self, location_type: str, current_url: str) -> List[Dict]:
        """Get location options (il, ilçe, mahalle) from current page"""
        try:
            logger.info(f"Getting {location_type} options...")

            self.driver.get(current_url)
            self.random_long_wait()  # Stealth: lokasyon listesi
            
            location_options = []
            location_selector = self.common_selectors.get("location_links")
            
            location_links = self.driver.find_elements(By.CSS_SELECTOR, location_selector)
            
            for link in location_links:
                try:
                    location_name = link.text.strip().split()[0]
                    location_url = link.get_attribute("href")

                    if location_name and location_url:
                        location_options.append({
                            'name': location_name,
                            'url': location_url
                        })
                except Exception:
                    continue
            
            # Display locations in 4 columns
            if location_options:
                print(f"\n{'=' * 80}")
                print(f"{location_type.upper()}")
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
            
            return location_options
            
        except Exception as e:
            logger.error(f"Error getting {location_type} options: {e}")
            return []
    
    def get_max_pages(self, target_url: Optional[str] = None) -> int:
        """Get maximum page count for a URL"""
        try:
            if target_url:
                self.driver.get(target_url)
                self.random_medium_wait()  # Stealth
            
            pagination_sel = self.common_selectors.get("pagination_list")
            active_sel = self.common_selectors.get("active_page")
            
            pagination = self.driver.find_elements(By.CSS_SELECTOR, pagination_sel)
            
            if not pagination:
                return 1
            
            page_numbers = []
            for item in pagination:
                try:
                    active_page = item.find_element(By.CSS_SELECTOR, active_sel)
                    page_numbers.append(int(active_page.text))
                except:
                    pass
                
                try:
                    page_link = item.find_element(By.CSS_SELECTOR, "a")
                    page_text = page_link.text
                    if page_text.isdigit():
                        page_numbers.append(int(page_text))
                except:
                    pass
            
            return max(page_numbers) if page_numbers else 1
            
        except Exception as e:
            logger.error(f"Error getting max pages: {e}")
            return 1
    
    def get_listing_count(self, url: str) -> str:
        """Get total listing count from page"""
        try:
            self.driver.get(url)
            self.random_medium_wait()  # Stealth
            
            # Try to find listing count element
            count_element = self.driver.find_elements(
                By.CSS_SELECTOR, "span.styles_adsCount__A1YW5 strong.styles_strong__cw1jn"
            )
            if count_element:
                return count_element[0].text.strip()
            
            # Alternative selector
            count_element = self.driver.find_elements(
                By.CSS_SELECTOR, "strong.styles_strong__cw1jn"
            )
            if count_element:
                return count_element[0].text.strip()
            
            return "?"
        except:
            return "?"
    
    def select_provinces(self, api_indices: Optional[List[int]] = None) -> List[Dict]:
        """Select provinces (cities) to scrape"""
        print(f"\n🏙️  İL SEÇİMİ")
        provinces = self.get_location_options("İller", self.base_url)
        if not provinces:
            print("❌ İl bulunamadı!")
            return []
        
        if api_indices:
             selected = [provinces[i - 1] for i in api_indices if 0 < i <= len(provinces)]
             if selected:
                 print(f"\n✅ API: {len(selected)} il seçildi")
                 return selected
             # Fallback if indices invalid
             return []

        print("\n🎯 ÇOKLU İL SEÇİMİ")
        print("Birden fazla seçim için: 1,3,5 veya 1-5")
        
        while True:
            user_input = input(f"\nİl numaralarını girin (1-{len(provinces)}): ").strip()
            if not user_input:
                print("❌ Boş giriş!")
                continue
            
            selections = self._parse_selection_input(user_input, len(provinces))
            if selections:
                selected = [provinces[i - 1] for i in selections]
                print(f"\n✅ {len(selected)} il seçildi:")
                for p in selected:
                    print(f"   - {p['name']}")
                return selected
            else:
                print("❌ Geçersiz seçim!")
    
    def select_districts_for_province(self, province: Dict, api_mode: bool = False, api_districts: Optional[List[str]] = None) -> tuple:
        """
        Select districts for a specific province.
        Returns: (districts, process_neighborhoods) tuple
        """
        print(f"\n🏘️  {province['name']} İLÇELERİ")
        districts = self.get_location_options("İlçeler", province['url'])
        
        if not districts:
            print(f"❌ {province['name']} için ilçe bulunamadı!")
            return ([province], False)  # Return province itself if no districts
        
        if api_mode:
            # In API mode, if specific districts provided by name, match them
            if api_districts:
                selected = [d for d in districts if d['name'] in api_districts]
                if selected:
                    for d in selected:
                        d['il'] = province['name']
                    return (selected, True) # Assume we want neighborhoods if specific districts selected? Or customize further.
                return ([], False) # Or fallback to all? Let's be strict for now.
            
            # If API mode but no districts, traverse ALL
            for d in districts:
                d['il'] = province['name']
            return (districts, True) # Process all districts

        print("\n1. Tüm ilçeleri tara (her ilçe için mahalle seç)")
        print("2. Tüm ili direkt tara (ilçe/mahalle seçimi yapma)")
        print("3. Belirli ilçeleri seç")
        print("4. Bu ili atla")
        
        choice = self.get_user_choice(4)
        
        if choice == 1:
            # Process all districts with neighborhood selection
            for d in districts:
                d['il'] = province['name']
            return (districts, True)  # process_neighborhoods = True
        elif choice == 2:
            return ([province], False)  # Scrape entire province directly
        elif choice == 4:
            return ([], False)  # Skip this province
        
        # Select specific districts
        print("\n🎯 İLÇE SEÇİMİ (örn: 1,3,5 veya 1-5)")
        user_input = input(f"İlçe numaralarını girin (1-{len(districts)}): ").strip()
        
        selections = self._parse_selection_input(user_input, len(districts))
        if selections:
            selected = [districts[i - 1] for i in selections]
            for d in selected:
                d['il'] = province['name']
            print(f"✅ {len(selected)} ilçe seçildi")
            return (selected, True)  # process_neighborhoods = True
        else:
            return ([province], False)  # Fallback to province
    
    def select_neighborhoods_for_district(self, district: Dict, api_mode: bool = False) -> List[Dict]:
        """Select neighborhoods for a specific district"""
        province_name = district.get('il', '')
        district_name = district['name']
        
        print(f"\n🏡 {province_name} / {district_name} MAHALLELERİ")
        neighborhoods = self.get_location_options("Mahalleler", district['url'])
        
        if not neighborhoods:
            return [district]  # Return district itself if no neighborhoods
        
        if api_mode:
            # API modunda tüm mahalleleri dön — mahalle bazlı scraping için
            for n in neighborhoods:
                n['il'] = province_name
                n['ilce'] = district_name
            return neighborhoods
        
        print("\n1. Tüm mahalleleri tara")
        print("2. Mahalle seç")
        print("3. Bu ilçeyi atla")
        
        choice = self.get_user_choice(3)
        
        if choice == 1:
            return [district]  # Scrape entire district
        elif choice == 3:
            return []  # Skip this district
        
        # Select specific neighborhoods
        print("\n🎯 MAHALLE SEÇİMİ (örn: 1,3,5 veya 1-5)")
        user_input = input(f"Mahalle numaralarını girin (1-{len(neighborhoods)}): ").strip()
        
        selections = self._parse_selection_input(user_input, len(neighborhoods))
        if selections:
            selected = [neighborhoods[i - 1] for i in selections]
            for n in selected:
                n['il'] = province_name
                n['ilce'] = district_name
            print(f"✅ {len(selected)} mahalle seçildi")
            return selected
        else:
            return [district]  # Fallback to district
    
    def _is_stop_requested(self) -> bool:
        """Check if stop has been requested"""
        return self._stop_checker is not None and self._stop_checker()

    def _is_listing_limit_reached(self) -> bool:
        """Check if max listing limit has been reached"""
        return self._max_listings > 0 and len(self.all_listings) >= self._max_listings

    def start_scraping_api(self, cities: Optional[List[str]] = None, districts: Optional[Dict[str, List[str]]] = None, max_listings: int = 0, progress_callback=None, stop_checker=None):
        """API entry point for scraping without user interaction"""
        self._stop_checker = stop_checker
        self._max_listings = max_listings

        subtype_info = f" ({self.subtype_name})" if self.subtype_name else ""
        limit_info = f" (limit: {max_listings} ilan)" if max_listings > 0 else " (limitsiz)"
        print(f"\n🚀 API: EmlakJet {self.listing_type.capitalize()} {self.category.capitalize()}{subtype_info} Scraper başlatılıyor{limit_info}")

        if progress_callback:
            progress_callback(f"{self.category.capitalize()}{subtype_info} taraması başlatılıyor...", 0, 100, 0)

        try:
            # subtype_path varsa onu kullan, yoksa base_url
            start_url = self.base_url
            if self.subtype_path:
                start_url = f"https://www.emlakjet.com{self.subtype_path}"
                print(f"📋 Alt kategori kullanılıyor: {self.subtype_path}")

            print("Getting province list...")
            all_provinces = self.get_location_options("İller", start_url)

            # Step 1: Select provinces
            if cities:
                api_indices = []
                cities_lower = [c.lower() for c in cities]
                for idx, p in enumerate(all_provinces, 1):
                    if p['name'].lower() in cities_lower:
                        api_indices.append(idx)

                if not api_indices:
                    logger.error(f"No matching provinces found for cities: {cities}")
                    logger.info(f"Available provinces: {[p['name'] for p in all_provinces[:5]]}...")
                    return

                provinces = self.select_provinces(api_indices=api_indices)
            else:
                logger.error("No cities provided for API scrape")
                return

            # Step 2: Process each province sequentially
            stopped = False
            for prov_idx, province in enumerate(provinces, 1):
                if self._is_stop_requested() or self._is_listing_limit_reached():
                    stopped = True
                    break

                # Get listing count for this province
                listing_count = self.get_listing_count(province['url'])

                print("\n" + "=" * 70)
                print(f"🏙️  İL {prov_idx}/{len(provinces)}: {province['name']} (Toplam İlan: {listing_count})")
                print("=" * 70)

                if progress_callback:
                    base_progress = ((prov_idx - 1) / len(provinces)) * 100
                    progress_callback(f"İşleniyor: {province['name']}...", prov_idx, len(provinces), base_progress)

                # İlçe filtreleme var mı kontrol et
                province_name = province['name']
                api_districts_for_province = None
                if districts and province_name in districts:
                    api_districts_for_province = districts[province_name]
                    logger.info(f"{province_name} için ilçe filtresi aktif: {api_districts_for_province}")

                # Select districts for this province
                selected_districts, process_neighborhoods = self.select_districts_for_province(
                    province,
                    api_mode=True,
                    api_districts=api_districts_for_province
                )

                if not selected_districts:
                    print(f"⏭️  {province['name']} atlandı.")
                    continue

                # Process each district
                for dist_idx, district in enumerate(selected_districts, 1):
                    if self._is_stop_requested() or self._is_listing_limit_reached():
                        stopped = True
                        break

                    # Check if this is province-level (no district selection)
                    if district.get('url') == province.get('url'):
                        targets = [{'url': province['url'], 'label': province['name'], 'type': 'il'}]
                    elif process_neighborhoods:
                        print(f"\n📍 İlçe {dist_idx}/{len(selected_districts)}: {district['name']}")
                        neighborhoods = self.select_neighborhoods_for_district(district, api_mode=True)
                        if not neighborhoods:
                            continue

                        if len(neighborhoods) == 1 and neighborhoods[0].get('url') == district.get('url'):
                            targets = [{'url': district['url'], 'label': f"{district.get('il', '')} / {district['name']}", 'type': 'ilce'}]
                        else:
                            targets = [{'url': n['url'], 'label': f"{n.get('il', '')} / {n.get('ilce', '')} / {n['name']}", 'type': 'mahalle'} for n in neighborhoods]
                    else:
                        targets = [{'url': district['url'], 'label': f"{district.get('il', '')} / {district['name']}", 'type': 'ilce'}]

                    # Scrape targets
                    total_targets = len(targets)
                    for target_idx, target in enumerate(targets, 1):
                        if self._is_stop_requested() or self._is_listing_limit_reached():
                            stopped = True
                            break

                        print(f"\n📍 Taranıyor: {target['label']} ({target_idx}/{total_targets})")

                        url_max_pages = self.get_max_pages(target['url'])
                        print(f"📊 {url_max_pages} sayfa mevcut, tamamı taranacak.")

                        # Her sayfa sonrası DB'ye anında kaydetme callback'i
                        def make_page_callback(prov_name, dist_name, tgt):
                            def _on_page_scraped(page_listings):
                                # Il/ilçe/mahalle bilgisini ekle
                                for listing in page_listings:
                                    listing['il'] = prov_name
                                    if tgt['type'] == 'mahalle':
                                        listing['ilce'] = dist_name
                                        listing['mahalle'] = tgt['label'].split('/')[-1].strip()
                                    elif tgt['type'] == 'ilce':
                                        listing['ilce'] = dist_name

                                # DB'ye anında kaydet
                                if self.db:
                                    from database import crud
                                    for data in page_listings:
                                        try:
                                            crud.upsert_listing(
                                                self.db,
                                                data=data,
                                                platform="emlakjet",
                                                kategori=self.category,
                                                ilan_tipi=self.listing_type,
                                                alt_kategori=self.subtype_name,
                                                scrape_session_id=self.scrape_session_id
                                            )
                                        except Exception as e:
                                            logger.warning(f"Sayfa bazlı DB kayıt hatası: {e}")
                                    try:
                                        self.db.commit()
                                        logger.info(f"💾 {len(page_listings)} ilan anında DB'ye kaydedildi")
                                    except Exception as e:
                                        logger.error(f"Sayfa bazlı DB commit hatası: {e}")
                                        self.db.rollback()
                            return _on_page_scraped

                        page_callback = make_page_callback(province['name'], district['name'], target)

                        listings_before = len(self.all_listings)
                        should_skip = self.scrape_pages(target['url'], url_max_pages, on_page_scraped=page_callback)

                        # Progress tracking
                        if progress_callback:
                            province_base = ((prov_idx - 1) / len(provinces)) * 100
                            province_range = 100 / len(provinces)
                            district_range = province_range / max(len(selected_districts), 1)
                            target_range = district_range / max(total_targets, 1)
                            overall = province_base + (dist_idx - 1) * district_range + target_idx * target_range

                            collected = len(self.all_listings)
                            limit_str = f" / {self._max_listings}" if self._max_listings > 0 else ""
                            progress_callback(
                                f"{province['name']} > {district['name']} > {target['label'].split('/')[-1].strip()}",
                                target_idx,
                                total_targets,
                                min(int(overall), 99),
                            )

                        if should_skip:
                            print("⏭️  Bu lokasyon atlandı.")
                        else:
                            print(f"   📦 Toplam: {len(self.all_listings)} ilan toplandı")

                    if stopped:
                        break
                if stopped:
                    break

            if self._is_listing_limit_reached():
                print(f"\n🎯 İlan limitine ulaşıldı: {len(self.all_listings)} / {self._max_listings}")
            
            # DB kaydetme sayfa bazlı yapılıyor
            if self.all_listings:
                print(f"\n✅ Scraping tamamlandı! Toplam {len(self.all_listings)} ilan bulundu.")
            else:
                print("\n❌ Hiç ilan bulunamadı!")

        except Exception as e:
            logger.error(f"API Scraping error: {e}")
            raise e

