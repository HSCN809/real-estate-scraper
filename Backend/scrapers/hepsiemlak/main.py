# -*- coding: utf-8 -*-
"""
HepsiEmlak Main Scraper - STEALTH MODE
Refactored with randomized delays to avoid bot detection
"""

import time
import random
import re
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
from core.config import get_hepsiemlak_config
from utils.logger import get_logger
from utils.data_exporter import DataExporter

from .parsers import KonutParser, ArsaParser, IsyeriParser, DevremulkParser, TuristikParser

logger = get_logger(__name__)


class HepsiemlakScraper(BaseScraper):
    """
    Main scraper for HepsiEmlak platform.
    Handles category selection, city filtering, and scraping.
    """
    
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
        listing_type: str = "satilik",  # 'satilik' or 'kiralik'
        category: str = "konut",
        subtype_path: Optional[str] = None,  # Yeni: Alt kategori URL path'i
        selected_cities: Optional[List[str]] = None,
        selected_districts: Optional[Dict[str, List[str]]] = None  # İl -> [İlçeler] mapping
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
        self.selected_districts = selected_districts or {}  # İlçe filtreleme
        self.subtype_path = subtype_path  # Kaydet

        # Alt kategori adını çıkar
        subtype_name = None
        if subtype_path:
            # /satilik/daire -> daire
            parts = subtype_path.strip('/').split('/')
            if len(parts) >= 2:
                subtype_name = parts[-1].replace('-', '_')

        # Hiyerarşik klasör yapısı: Outputs/HepsiEmlak Output/{listing_type}/{category}/{subtype}/
        self.exporter = DataExporter(
            output_dir="Outputs/HepsiEmlak Output",
            listing_type=listing_type,
            category=category,
            subtype=subtype_name
        )
        self.current_category = category
        
        # Initialize the appropriate parser
        parser_class = self.CATEGORY_PARSERS.get(category, KonutParser)
        self.parser = parser_class()
    
    @property
    def subtype_name(self) -> Optional[str]:
        """Extract subtype name from subtype_path for file naming"""
        if self.subtype_path:
            # /satilik/daire -> daire
            parts = self.subtype_path.strip('/').split('/')
            if len(parts) >= 2:
                return parts[-1].replace('-', '_')
        return None
    
    def get_file_prefix(self) -> str:
        """Generate file prefix with subtype if available"""
        if self.subtype_name:
            return f"hepsiemlak_{self.listing_type}_{self.category}_{self.subtype_name}"
        return f"hepsiemlak_{self.listing_type}_{self.category}"
    
    def extract_listing_data(self, container) -> Optional[Dict[str, Any]]:
        """Use the category parser to extract listing data"""
        return self.parser.extract_listing_data(container)
    
    def parse_category_details(self, quick_info: str, title: str) -> Dict[str, Any]:
        """Not used for HepsiEmlak - parsing is done via extract_category_data"""
        return {}
    
    def get_cities(self) -> List[str]:
        """Get all cities and let user select"""
        print(f"\n{self.category.capitalize()} sitesine gidiliyor...")
        self.driver.get(self.base_url)
        time.sleep(5)  # HepsiEmlak için sabit 5 saniye - sayfa tam yüklensin
        
        try:
            # Find city dropdown
            city_dropdown_sel = self.common_selectors.get("city_dropdown")
            city_dropdown = self.wait_for_clickable(city_dropdown_sel)
            
            if not city_dropdown:
                logger.error("City dropdown not found")
                return []
            
            # JS click ile menüyü aç (Selenium'un objeye tıklayamama riskine karşı)
            self.driver.execute_script("arguments[0].click();", city_dropdown)
            print("Şehir dropdown'ı açıldı...")
            time.sleep(3)  # Dropdown açılması için 3 saniye
            
            # Expand dropdown
            city_list_sel = self.common_selectors.get("city_list")
            dropdown_container = self.wait_for_element(city_list_sel)
            
            if dropdown_container:
                self.driver.execute_script("""
                    var container = arguments[0];
                    container.style.maxHeight = 'none';
                    container.style.overflow = 'visible';
                    container.style.height = 'auto';
                """, dropdown_container)
            time.sleep(2)  # Liste genişletme sonrası bekleme
            
            if not dropdown_container:
                logger.error("City list container not showing after click")
                return []
            
            # Get city items
            city_item_sel = self.common_selectors.get("city_item")
            city_link_sel = self.common_selectors.get("city_link")
            
            city_items = self.driver.find_elements(By.CSS_SELECTOR, city_item_sel)
            
            cities = []
            for city_item in city_items:
                try:
                    city_link = city_item.find_element(By.CSS_SELECTOR, city_link_sel)
                    city_name = city_link.text.strip()
                    if city_name and city_name != "İl Seçiniz" and city_name not in cities:
                        cities.append(city_name)
                except:
                    continue
            
            cities.sort()
            
            # Display cities in 4 columns
            print("\n" + "=" * 80)
            print("TÜM ŞEHİRLER")
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
            
            print(f"\nToplam {len(cities)} şehir bulundu.")
            
            # Close dropdown
            try:
                self.driver.execute_script("document.elementFromPoint(10, 10).click();")
            except:
                pass
            self.random_short_wait()  # Stealth
            
            return cities
            
            return cities
            
        except Exception as e:
            logger.error(f"Error getting cities: {e}")
            return []
            
    def get_cities_api(self) -> List[str]:
        """Get cities logic for API (non-interactive)"""
        # We need to open the dropdown to get the list, similar to get_cities but without printing?
        # Or just reuse get_cities but suppress print/interaction? 
        # Actually get_cities interacts with DOM, so it is required.
        # Let's modify get_cities to be quieter or just use it.
        # But get_cities prints a lot.
        
        # We'll just define this as an alias or use get_cities directly if needed.
        return self.get_cities()
    
    def select_cities(self, cities: List[str]) -> List[str]:
        """Let user select multiple cities"""
        selected = []
        
        print("\n" + "=" * 50)
        print("ŞEHİR SEÇİM SEÇENEKLERİ")
        print("=" * 50)
        print("1. Tek tek şehir seç (örn: 1,3,5)")
        print("2. Aralık seç (örn: 1-5)")
        print("3. Tüm şehirleri seç")
        print("4. Şehir sil")
        print("5. Seçimi bitir")
        
        while True:
            print(f"\nSeçili şehirler ({len(selected)}): {selected}")
            option = input("\nSeçenek (1-5): ").strip()
            
            if option == "5":
                if selected:
                    print(f"\nSeçim tamamlandı: {', '.join(selected)}")
                    return selected
                else:
                    print("En az bir şehir seçmelisiniz!")
            
            elif option == "3":
                selected = cities.copy()
                print("Tüm şehirler seçildi!")
            
            elif option == "4":
                if not selected:
                    print("Silinecek şehir yok!")
                    continue
                
                print("\nMevcut seçili şehirler:")
                for i, city in enumerate(selected, 1):
                    print(f"{i}. {city}")
                
                delete_input = input("\nSilmek istediğiniz numaraları girin: ").strip()
                indices = self._parse_selection_input(delete_input, len(selected))
                
                # Remove in reverse order to maintain indices
                for idx in sorted(indices, reverse=True):
                    removed = selected.pop(idx - 1)
                    print(f"✓ {removed} silindi")
            
            elif option == "2":
                range_input = input("Aralık girin (örn: 1-5): ").strip()
                indices = self._parse_selection_input(range_input, len(cities))
                for idx in indices:
                    if cities[idx - 1] not in selected:
                        selected.append(cities[idx - 1])
                print(f"{len(indices)} şehir eklendi.")
            
            elif option == "1":
                user_input = input("Şehir numaralarını girin (örn: 1,3,5): ").strip()
                indices = self._parse_selection_input(user_input, len(cities))
                for idx in indices:
                    if cities[idx - 1] not in selected:
                        selected.append(cities[idx - 1])
                        print(f"Seçilen: {cities[idx - 1]}")
            
            else:
                print("Geçersiz seçenek!")
        
        return selected
            
    def select_cities_api(self, all_cities: List[str], target_cities: Optional[List[str]] = None) -> List[str]:
        """Select cities for API"""
        if not target_cities:
            return []
        
        selected = []
        for city in target_cities:
            # Simple fuzzy match or exact match
            # "istanbul" -> "İstanbul"
            # We try to match user input to available cities
            
            # Direct match
            if city in all_cities:
                selected.append(city)
                continue
                
            # Case insensitive match
            found = False
            for ac in all_cities:
                if ac.lower() == city.lower():
                    selected.append(ac)
                    found = True
                    break
            if not found:
                 logger.warning(f"City not found: {city}")
        
        return selected
    
    def select_single_city(self, city_name: str) -> bool:
        """Select a single city - DOĞRUDAN ŞEHİR URL'İNE GİT"""
        try:
            import unicodedata
            
            # Unicode normalizasyonu (NFC -> composed form)
            city_slug = unicodedata.normalize('NFC', city_name)
            
            # Türkçe karakter dönüşümleri - önce büyük harfleri çevir
            tr_upper = {'İ': 'i', 'I': 'i', 'Ğ': 'g', 'Ü': 'u', 'Ş': 's', 'Ö': 'o', 'Ç': 'c'}
            for tr, en in tr_upper.items():
                city_slug = city_slug.replace(tr, en)
            
            # Sonra küçük harfe çevir ve küçük Türkçe karakterleri dönüştür
            city_slug = city_slug.lower()
            tr_lower = {'ı': 'i', 'ğ': 'g', 'ü': 'u', 'ş': 's', 'ö': 'o', 'ç': 'c'}
            for tr, en in tr_lower.items():
                city_slug = city_slug.replace(tr, en)
            
            city_slug = city_slug.replace(' ', '-')
            
            # Subtype path varsa onu kullan, yoksa kategori path'ini config'den al
            if self.subtype_path:
                # Subtype path: /kiralik/tarla -> tarla
                # Şehir URL: eskisehir-kiralik/tarla
                path_parts = self.subtype_path.split('/')
                # path_parts: ['', 'kiralik', 'tarla']
                if len(path_parts) >= 3:
                    category_suffix = "/" + path_parts[2]  # /tarla
                else:
                    category_suffix = ""
                print(f"DEBUG: Using subtype_path: {self.subtype_path} -> category_suffix: {category_suffix}")
            else:
                # Kategori path'ini config'den al
                # Örnek: /kiralik/turistik-isletme -> /turistik-isletme (sadece kategori kısmı)
                category_path = self.hepsiemlak_config.categories.get(self.listing_type, {}).get(self.current_category, '')
                
                # Category path'ten listing_type'ı çıkar (zaten URL'de olacak)
                # /kiralik/turistik-isletme -> /turistik-isletme
                # /satilik/arsa -> /arsa
                # /kiralik -> "" (konut için)
                category_suffix = ""
                if category_path:
                    # "/kiralik/arsa" -> ["", "kiralik", "arsa"] -> "arsa"
                    # "/kiralik" -> ["", "kiralik"] -> "" (konut)
                    parts = category_path.split('/')
                    if len(parts) > 2:
                        category_suffix = "/" + parts[2]  # /arsa, /isyeri, /turistik-isletme vb.
            
            # Doğrudan şehir + kategori sayfasına git
            # Örnek: https://www.hepsiemlak.com/eskisehir-kiralik/turistik-isletme
            city_url = f"https://www.hepsiemlak.com/{city_slug}-{self.listing_type}{category_suffix}"
            print(f"Şehir URL'sine gidiliyor: {city_url}")
            print(f"DEBUG: listing_type = {self.listing_type}, category = {self.current_category}, subtype_path = {self.subtype_path}")
            
            self.driver.get(city_url)
            time.sleep(5)  # Sayfa tam yüklensin
            
            # URL doğru mu kontrol et
            current_url = self.driver.current_url
            if city_slug in current_url:
                print(f"✓ {city_name} sayfası yüklendi")
                return True
            else:
                print(f"✗ {city_name} sayfasına gidilemedi. URL: {current_url}")
                return False
            
        except Exception as e:
            logger.error(f"Error selecting city {city_name}: {e}")
            return False

    @staticmethod
    def normalize_string(s: str) -> str:
        """Türkçe karakter normalize - fuzzy matching için"""
        import unicodedata
        s = s.lower().strip()
        # Türkçe karakterleri değiştir
        replacements = {'ı': 'i', 'ğ': 'g', 'ü': 'u', 'ş': 's', 'ö': 'o', 'ç': 'c', 'İ': 'i'}
        for old, new in replacements.items():
            s = s.replace(old, new)
        return unicodedata.normalize('NFKD', s)

    def select_single_district(self, district_name: str) -> bool:
        """İlçe için doğrudan URL'e git - dropdown kullanma"""
        try:
            import unicodedata

            # Unicode normalizasyonu (NFC -> composed form)
            district_slug = unicodedata.normalize('NFC', district_name)

            # Türkçe karakter dönüşümleri - önce büyük harfleri çevir
            tr_upper = {'İ': 'i', 'I': 'i', 'Ğ': 'g', 'Ü': 'u', 'Ş': 's', 'Ö': 'o', 'Ç': 'c'}
            for tr, en in tr_upper.items():
                district_slug = district_slug.replace(tr, en)

            # Sonra küçük harfe çevir ve küçük Türkçe karakterleri dönüştür
            district_slug = district_slug.lower()
            tr_lower = {'ı': 'i', 'ğ': 'g', 'ü': 'u', 'ş': 's', 'ö': 'o', 'ç': 'c'}
            for tr, en in tr_lower.items():
                district_slug = district_slug.replace(tr, en)

            district_slug = district_slug.replace(' ', '-')

            # Subtype path varsa onu kullan, yoksa kategori path'ini config'den al
            if self.subtype_path:
                # Subtype path: /kiralik/tarla -> tarla
                # İlçe URL: akyurt-kiralik/tarla
                path_parts = self.subtype_path.split('/')
                if len(path_parts) >= 3:
                    category_suffix = "/" + path_parts[2]  # /tarla
                else:
                    category_suffix = ""
            else:
                # Kategori path'ini config'den al
                category_path = self.hepsiemlak_config.categories.get(self.listing_type, {}).get(self.current_category, '')
                category_suffix = ""
                if category_path:
                    parts = category_path.split('/')
                    if len(parts) > 2:
                        category_suffix = "/" + parts[2]  # /arsa, /isyeri, /turistik-isletme vb.

            # Doğrudan ilçe + kategori sayfasına git
            # Örnek: https://www.hepsiemlak.com/akyurt-satilik
            district_url = f"https://www.hepsiemlak.com/{district_slug}-{self.listing_type}{category_suffix}"
            print(f"📍 İlçe URL'sine gidiliyor: {district_url}")

            self.driver.get(district_url)
            time.sleep(5)  # Sayfa tam yüklensin

            # URL doğru mu kontrol et
            current_url = self.driver.current_url
            if district_slug in current_url:
                print(f"✓ {district_name} sayfası yüklendi")
                return True
            else:
                print(f"✗ {district_name} sayfasına gidilemedi. URL: {current_url}")
                return False

        except Exception as e:
            logger.error(f"Error selecting district {district_name}: {e}")
            return False

    def search_listings(self) -> bool:
        """Click search button and wait for results"""
        try:
            search_selectors = self.common_selectors.get("search_buttons", [])
            
            for selector in search_selectors:
                try:
                    search_button = self.wait_for_clickable(selector, timeout=5)
                    if search_button:
                        self.driver.execute_script("arguments[0].click();", search_button)
                        print("Arama yapılıyor...")
                        self.random_long_wait()  # Stealth: arama sonrası
                        
                        # Wait for results
                        results_sel = self.common_selectors.get("listing_results")
                        self.wait_for_element(results_sel)
                        return True
                except:
                    continue
            
            print("Arama butonu bulunamadı")
            return False
            
        except Exception as e:
            logger.error(f"Search error: {e}")
            return False
    
    def get_total_pages(self) -> int:
        """Get total number of pages from pagination"""
        try:
            # Pagination linklerini bul (retry mekanizması ile)
            max_retries = 3
            page_links = []
            
            for retry in range(max_retries):
                page_links = self.driver.find_elements(
                    By.CSS_SELECTOR, 
                    "ul.he-pagination__links li.he-pagination__item a.he-pagination__link"
                )
                
                if page_links:
                    break
                elif retry < max_retries - 1:
                    print(f"⚠️ Pagination bulunamadı, tekrar deneniyor... ({retry + 1}/{max_retries})")
                    time.sleep(2)
            
            # Sayfa sayısını bul - en büyük sayıyı al
            max_page = 1
            for link in page_links:
                text = link.text.strip()
                
                # Sadece rakam olan linkleri kontrol et (1, 2, 3, ..., 421 gibi)
                if text.isdigit():
                    page_num = int(text)
                    if page_num > max_page:
                        max_page = page_num
            
            print(f"DEBUG: max_page = {max_page}")
            return max_page
            
        except Exception as e:
            logger.warning(f"Pagination detection failed: {e}")
            return 1
    
    def scrape_city(self, city: str, max_pages: int = None, api_mode: bool = False, progress_callback=None) -> List[Dict[str, Any]]:
        """Scrape all listings for a single city"""
        print(f"\n{'=' * 70}")
        print(f"🏙️  {city.upper()} - TÜM İLÇELER TARANACAK")
        print("=" * 70)
        
        if progress_callback:
            progress_callback(f"{city} için tarama başlatılıyor...", current=0, total=100)
            
        try:
            # Select city (doğrudan şehir URL'ine gider)
            if not self.select_single_city(city):
                logger.error(f"❌ {city} seçilemedi, atlanıyor")
                return []

            # Artık search_listings'e gerek yok - doğrudan şehir sayfasındayız

            # Check for zero results
            try:
                zero_check = self.driver.find_elements(
                    By.XPATH, "//span[contains(text(), 'için 0 ilan bulundu')]"
                )
                if zero_check:
                    print(f"⚠️  {city} için 0 ilan bulundu")
                    logger.info(f"🔍 {city} - İlan bulunamadı")
                    return []
            except:
                pass

            # Get total pages
            total_pages = self.get_total_pages()
            print(f"📊 {city} için toplam {total_pages} sayfa tespit edildi")
            
            # Get page count
            if api_mode:
                 if max_pages:
                     pages_to_scrape = min(max_pages, total_pages)
                 else:
                     pages_to_scrape = 1 # Default 1 if not specified
            else:
                if total_pages > 1:
                    try:
                        user_input = input(f"{city} için kaç sayfa taranacak? (1-{total_pages}): ").strip()
                        pages_to_scrape = min(int(user_input), total_pages)
                        if pages_to_scrape < 1:
                            pages_to_scrape = 1
                    except ValueError:
                        pages_to_scrape = min(3, total_pages)
                        print(f"Geçersiz giriş, varsayılan {pages_to_scrape} sayfa kullanılıyor.")
                else:
                    pages_to_scrape = 1
            
            city_listings = []
            
            # Scrape pages
            for page in range(1, pages_to_scrape + 1):
                print(f"\n📄 Sayfa {page}/{pages_to_scrape} taranıyor...")

                if progress_callback:
                    # Progress: tamamlanan sayfa sayısı üzerinden hesapla
                    # Sayfa 5 taranmaya başladığında 4 tamamlanmış = %80
                    completed_pages = page - 1
                    page_progress = int((completed_pages / pages_to_scrape) * 100)
                    progress_callback(f"{city} - Sayfa {page}/{pages_to_scrape} taranıyor...", current=page, total=pages_to_scrape, progress=page_progress)

                if page > 1:
                    # Şehir URL'ini kullan (base_url değil!)
                    current_city_url = self.driver.current_url.split('?')[0]
                    page_url = f"{current_city_url}?page={page}"
                    self.driver.get(page_url)
                    self.random_long_wait()  # Stealth: sayfa geçişi
                    self.wait_for_element(self.common_selectors.get("listing_results"))

                page_listings = self.scrape_current_page()
                city_listings.extend(page_listings)

                print(f"   ✓ {len(page_listings)} ilan işlendi")

                if page < pages_to_scrape:
                    self.random_medium_wait()  # Stealth: sayfalar arası

            print(f"\n{'=' * 70}")
            print(f"✅ {city.upper()} TAMAMLANDI")
            print(f"📊 Toplam {len(city_listings)} ilan toplandı")
            print("=" * 70)

            logger.info(f"✅ {city} - {len(city_listings)} ilan toplandı")
            return city_listings

        except Exception as e:
            logger.error(f"❌ {city} tarama hatası: {e}")
            return []

    def scrape_city_with_districts(self, city: str, districts: List[str], max_pages: int = None, progress_callback=None) -> Dict[str, List[Dict[str, Any]]]:
        """
        Bir şehir için belirtilen ilçeleri scrape et - HER İLÇEYİ AYRI AYRI TARA VE KAYDET

        Returns:
            Dictionary of district -> list of listings (her ilçe için ayrı)
        """
        all_results = {}  # İlçe -> İlanlar mapping

        print(f"\n{'=' * 70}")
        print(f"🏙️  {city.upper()} - İLÇE FİLTRELİ TARAMA")
        print("=" * 70)

        # İlçe seçimi yoksa tüm şehri scrape et
        if not districts or len(districts) == 0:
            logger.info(f"📍 {city} - Tüm ilçeler taranıyor")
            # Şehir bazlı kayıt için eski formatta döndür
            city_listings = self.scrape_city(city, max_pages, api_mode=True, progress_callback=progress_callback)
            return {city: city_listings}

        print(f"📋 Seçili ilçeler: {', '.join(districts)}")
        logger.info(f"🎯 {city} - {len(districts)} ilçe ayrı ayrı taranacak")

        # Her ilçeyi ayrı ayrı tara
        for idx, district in enumerate(districts, 1):
            print(f"\n{'=' * 60}")
            print(f"📍 İLÇE {idx}/{len(districts)}: {district.upper()}")
            print("=" * 60)

            district_listings = []  # Bu ilçenin ilanları

            try:
                # Doğrudan ilçe URL'ine git
                if not self.select_single_district(district):
                    logger.warning(f"⚠️  {district} ilçesi yüklenemedi, atlanıyor")
                    continue

                # Check for zero results
                try:
                    zero_check = self.driver.find_elements(
                        By.XPATH, "//span[contains(text(), 'için 0 ilan bulundu')]"
                    )
                    if zero_check:
                        print(f"⚠️  {district} için 0 ilan bulundu")
                        logger.info(f"🔍 {district} - İlan bulunamadı")
                        continue
                except:
                    pass

                # Get total pages
                total_pages = self.get_total_pages()
                print(f"📊 {district} için toplam {total_pages} sayfa tespit edildi")

                pages_to_scrape = min(max_pages, total_pages) if max_pages else 1

                # Scrape pages for this district
                for page in range(1, pages_to_scrape + 1):
                    print(f"\n📄 Sayfa {page}/{pages_to_scrape} taranıyor...")

                    if progress_callback:
                        # Progress: ilçe ve sayfa bilgisini birlikte göster
                        overall_progress = int(((idx - 1 + (page / pages_to_scrape)) / len(districts)) * 100)
                        progress_callback(
                            f"{district} - Sayfa {page}/{pages_to_scrape}",
                            current=idx,
                            total=len(districts),
                            progress=overall_progress
                        )

                    if page > 1:
                        current_district_url = self.driver.current_url.split('?')[0]
                        page_url = f"{current_district_url}?page={page}"
                        self.driver.get(page_url)
                        self.random_long_wait()
                        self.wait_for_element(self.common_selectors.get("listing_results"))

                    page_listings = self.scrape_current_page()
                    district_listings.extend(page_listings)

                    print(f"   ✓ {len(page_listings)} ilan işlendi")

                    if page < pages_to_scrape:
                        self.random_medium_wait()

                # İlçe verilerini kaydet
                if district_listings:
                    all_results[district] = district_listings
                    print(f"\n✅ {district} tamamlandı - {len(district_listings)} ilan")

                    # Her ilçeyi hemen kaydet (bellek tasarrufu ve güvenlik için)
                    self._save_district_data(city, district, district_listings)
                else:
                    print(f"\n⚠️  {district} - İlan bulunamadı")

                # İlçeler arası bekleme
                if idx < len(districts):
                    self.random_medium_wait()

            except Exception as e:
                logger.error(f"❌ {district} tarama hatası: {e}")
                continue

        total_listings = sum(len(listings) for listings in all_results.values())
        print(f"\n{'=' * 70}")
        print(f"✅ {city.upper()} - TÜM İLÇELER TAMAMLANDI")
        print(f"📊 Toplam {total_listings} ilan toplandı")
        print(f"🎯 Taranan ilçeler: {', '.join(all_results.keys())}")
        print("=" * 70)

        logger.info(f"✅ {city} - {total_listings} ilan toplandı ({len(all_results)} ilçe)")
        return all_results

    def _save_district_data(self, city: str, district: str, listings: List[Dict[str, Any]]):
        """Her ilçe için ayrı klasörde dosya kaydet"""
        if not listings:
            return

        # Türkçe karakter normalizasyonu
        import unicodedata

        def normalize_name(name: str) -> str:
            """Klasör adı için normalize et"""
            name = unicodedata.normalize('NFC', name)
            replacements = {
                'İ': 'i', 'I': 'i', 'Ğ': 'g', 'Ü': 'u', 'Ş': 's', 'Ö': 'o', 'Ç': 'c',
                'ı': 'i', 'ğ': 'g', 'ü': 'u', 'ş': 's', 'ö': 'o', 'ç': 'c'
            }
            for tr, en in replacements.items():
                name = name.replace(tr, en)
            return name.lower().replace(' ', '_')

        city_slug = normalize_name(city)
        district_slug = normalize_name(district)

        # Klasör yapısı: .../satilik/konut/daire/ankara/cankaya/
        subfolder = f"{city_slug}/{district_slug}"

        # Dosya prefix: hepsiemlak_satilik_konut_daire_ankara_cankaya
        file_prefix = f"{self.get_file_prefix()}_{city_slug}_{district_slug}"

        try:
            self.exporter.save_excel(
                listings,
                prefix=file_prefix,
                timestamp=True,
                subfolder=subfolder
            )
            logger.info(f"💾 {city}/{district} - {len(listings)} ilan kaydedildi")
        except Exception as e:
            logger.error(f"❌ {city}/{district} kaydetme hatası: {e}")

    def scrape_current_page(self) -> List[Dict[str, Any]]:
        """Scrape all listings on current page"""
        listings = []

        try:
            container_sel = self.common_selectors.get("listing_container")
            self.wait_for_element(self.common_selectors.get("listing_results"))

            elements = self.driver.find_elements(By.CSS_SELECTOR, container_sel)
            print(f"   🔍 {len(elements)} ilan elementi bulundu")

            for element in elements:
                try:
                    data = self.parser.extract_listing_data(element)
                    if data:
                        listings.append(data)
                    time.sleep(random.uniform(0.02, 0.08))  # Stealth
                except Exception as e:
                    continue

            print(f"   ✓ {len(listings)} ilan başarıyla parse edildi")

        except Exception as e:
            logger.error(f"❌ Sayfa tarama hatası: {e}")

        return listings
    
    def start_scraping_api(self, max_pages: int = 1, progress_callback=None):
        """API scraping entry point"""
        print(f"\n🚀 API: HepsiEmlak {self.listing_type.capitalize()} {self.category.capitalize()} Scraper")
        
        try:
            # For HepsiEmlak, current logic requires digging into DOM to get city list to click them.
            # get_cities() does that.
            
            # If self.selected_cities is already populated (from init), we can use that filter.
            # But we need to VALIDATE if those cities exist and get their clickable elements maybe?
            # scrape_city() calls select_single_city() which opens dropdown and clicks.
            # So we just need list of strings.
            
            if not self.selected_cities:
                 logger.error("No cities provided for API scrape")
                 return

            # Scrape each city
            all_results = {}
            total_listings_count = 0

            for city in self.selected_cities:
                # Durdurma kontrolü - kullanıcı durdur dediyse mevcut verileri kaydet
                from api.status import task_status
                if task_status.is_stop_requested():
                    print(f"\n⚠️ Durdurma isteği alındı! {len(all_results)} şehir tarandı.")
                    task_status.stopped_early = True
                    break

                # İlçe filtreleme var mı kontrol et
                if self.selected_districts and city in self.selected_districts:
                    districts = self.selected_districts[city]
                    logger.info(f"🎯 {city} için ilçe filtresi aktif: {len(districts)} ilçe")
                    print(f"📍 İlçeler: {', '.join(districts)}")

                    # scrape_city_with_districts artık Dict[district -> listings] döndürüyor
                    # VE her ilçeyi otomatik olarak kaydediyor
                    district_results = self.scrape_city_with_districts(
                        city,
                        districts=districts,
                        max_pages=max_pages,
                        progress_callback=progress_callback
                    )

                    # Sadece istatistik için tutuyoruz (zaten kaydedildi)
                    if district_results:
                        all_results[city] = district_results
                        total_listings_count += sum(len(listings) for listings in district_results.values())
                else:
                    # İlçe seçimi yoksa tüm şehri tara ve kaydet
                    logger.info(f"📍 {city} - Tüm ilçeler taranacak (filtre yok)")
                    city_listings = self.scrape_city(
                        city,
                        max_pages=max_pages,
                        api_mode=True,
                        progress_callback=progress_callback
                    )

                    if city_listings:
                        # Şehir bazlı kayıt
                        all_results[city] = city_listings
                        total_listings_count += len(city_listings)

                        # Şehir bazlı tarama için kaydet
                        print(f"\n💾 {city} verileri kaydediliyor...")
                        self.exporter.save_by_city(
                            {city: city_listings},
                            prefix=self.get_file_prefix(),
                            format="excel"
                        )

                self.random_medium_wait()  # Stealth: şehirler arası

            # Özet bilgi (veriler zaten kaydedildi)
            if all_results:
                total = total_listings_count

                print(f"\n{'=' * 70}")
                if task_status.stopped_early:
                    print("⚠️  ERKEN DURDURULDU")
                    logger.warning(f"⚠️  Tarama erken durduruldu: {len(all_results)} şehir, {total} ilan")
                else:
                    print("✅ TARAMA BAŞARIYLA TAMAMLANDI")
                    logger.info(f"✅ Tarama tamamlandı: {len(all_results)} şehir, {total} ilan")

                print(f"📊 Taranan Şehir Sayısı: {len(all_results)}")
                print(f"📊 Toplam İlan Sayısı: {total}")

                # Her şehir için detay
                for city, data in all_results.items():
                    if isinstance(data, dict):
                        # İlçe bazlı tarama yapıldı
                        total_city = sum(len(listings) for listings in data.values())
                        print(f"   • {city}: {total_city} ilan ({len(data)} ilçe)")
                        for district, listings in data.items():
                            print(f"      - {district}: {len(listings)} ilan")
                    else:
                        # Şehir bazlı tarama
                        print(f"   • {city}: {len(data)} ilan")

                print("=" * 70)
            else:
                print(f"\n{'=' * 70}")
                print("❌ HİÇ İLAN BULUNAMADI")
                print("=" * 70)
                logger.warning("⚠️  Hiç ilan bulunamadı")

        except Exception as e:
            logger.error(f"❌ API tarama hatası: {e}")
            raise e

    def start_scraping(self):
        """Main scraping entry point"""
        print(f"\n🚀 HepsiEmlak {self.listing_type.capitalize()} {self.category.capitalize()} Scraper")
        
        try:
            # Get cities
            cities = self.get_cities()
            if not cities:
                print("❌ Şehir bulunamadı!")
                return
            
            # Select cities
            selected_cities = self.select_cities(cities)
            if not selected_cities:
                print("❌ Şehir seçilmedi!")
                return
            
            # Scrape each city
            all_results = {}
            for city in selected_cities:
                city_listings = self.scrape_city(city)
                if city_listings:
                    all_results[city] = city_listings
                self.random_medium_wait()  # Stealth: şehirler arası
            
            # Save data
            if all_results:
                self.exporter.save_by_city(
                    all_results,
                    prefix=self.get_file_prefix(),
                    format="excel",
                    city_district_map=self.selected_districts if self.selected_districts else None
                )
                
                total = sum(len(v) for v in all_results.values())
                print(f"\n🎉 TOPLAM: {len(all_results)} şehir, {total} ilan")
            else:
                print("❌ Hiç ilan bulunamadı!")
            
        except KeyboardInterrupt:
            print("\n⏹️  İşlem kullanıcı tarafından iptal edildi.")
            if all_results:
                self.exporter.save_by_city(
                    all_results,
                    prefix=f"{self.get_file_prefix()}_partial",
                    format="excel",
                    city_district_map=self.selected_districts if self.selected_districts else None
                )
                total = sum(len(v) for v in all_results.values())
                print(f"💾 {len(all_results)} şehir, {total} ilan kaydedildi.")
        except Exception as e:
            logger.error(f"Scraping error: {e}")
            print(f"❌ Hata: {e}")


def main():
    """Main entry point for HepsiEmlak scraper"""
    print("\n" + "=" * 60)
    print("🏠 HEPSİEMLAK SCRAPER")
    print("=" * 60)
    
    # Listing type selection
    print("\nİlan Tipi Seçin:")
    print("1. Satılık")
    print("2. Kiralık")
    print("3. Çıkış")
    
    try:
        type_choice = int(input("\nSeçiminiz (1-3): "))
        if type_choice == 3:
            print("👋 Çıkış yapılıyor...")
            return
        
        listing_type = "satilik" if type_choice == 1 else "kiralik"
    except ValueError:
        print("❌ Geçersiz giriş!")
        return
    
    # Category selection
    categories = ['konut', 'arsa', 'isyeri', 'devremulk', 'turistik_isletme']
    print("\nKategori Seçin:")
    for i, cat in enumerate(categories, 1):
        print(f"{i}. {cat.capitalize()}")
    print(f"{len(categories) + 1}. Çıkış")
    
    try:
        choice = int(input(f"\nSeçiminiz (1-{len(categories) + 1}): "))
        if choice == len(categories) + 1:
            print("👋 Çıkış yapılıyor...")
            return
        
        if 1 <= choice <= len(categories):
            category = categories[choice - 1]
        else:
            print("❌ Geçersiz seçim!")
            return
    except ValueError:
        print("❌ Geçersiz giriş!")
        return
    
    # Start scraper
    manager = DriverManager()
    
    try:
        driver = manager.start()
        
        scraper = HepsiemlakScraper(driver, listing_type, category)
        scraper.start_scraping()
        
    except Exception as e:
        logger.error(f"Error: {e}")
        print(f"❌ Hata: {e}")
    
    finally:
        manager.stop()


if __name__ == "__main__":
    main()
