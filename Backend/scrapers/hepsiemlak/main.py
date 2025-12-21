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
        selected_cities: Optional[List[str]] = None
    ):
        base_config = get_hepsiemlak_config()
        category_path = base_config.categories.get(listing_type, {}).get(category, '')
        base_url = base_config.base_url + category_path
        
        super().__init__(driver, base_url, "hepsiemlak", category)
        
        self.listing_type = listing_type
        self.hepsiemlak_config = base_config
        self.selected_cities = selected_cities or []
        # Output: Outputs/HepsiEmlak Output/{category}/
        self.exporter = DataExporter(output_dir=f"Outputs/HepsiEmlak Output/{category}")
        self.current_category = category
        
        # Initialize the appropriate parser
        parser_class = self.CATEGORY_PARSERS.get(category, KonutParser)
        self.parser = parser_class()
    
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
        self.random_long_wait()  # Stealth: rastgele 2-4 sn
        
        try:
            # Find city dropdown
            city_dropdown_sel = self.common_selectors.get("city_dropdown")
            city_dropdown = self.wait_for_clickable(city_dropdown_sel)
            
            if not city_dropdown:
                logger.error("City dropdown not found")
                return []
            
            city_dropdown.click()
            print("Şehir dropdown'ı açıldı...")
            self.random_medium_wait()  # Stealth: rastgele 1-2.5 sn
            
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
            self.random_medium_wait()  # Stealth
            
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
        """Select a single city in the filter"""
        try:
            # Refresh page
            self.driver.get(self.base_url)
            self.random_long_wait()  # Stealth
            
            # Open city dropdown
            city_dropdown_sel = self.common_selectors.get("city_dropdown")
            city_dropdown = self.wait_for_clickable(city_dropdown_sel)
            
            if not city_dropdown:
                return False
            
            city_dropdown.click()
            self.random_medium_wait()  # Stealth
            
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
            self.random_medium_wait()  # Stealth
            
            # Find and select city
            city_item_sel = self.common_selectors.get("city_item")
            city_link_sel = self.common_selectors.get("city_link")
            city_radio_sel = self.common_selectors.get("city_radio")
            
            city_items = self.driver.find_elements(By.CSS_SELECTOR, city_item_sel)
            
            for city_item in city_items:
                try:
                    city_link = city_item.find_element(By.CSS_SELECTOR, city_link_sel)
                    if city_link.text.strip() == city_name:
                        try:
                            radio = city_item.find_element(By.CSS_SELECTOR, city_radio_sel)
                            self.driver.execute_script("arguments[0].click();", radio)
                        except:
                            self.driver.execute_script("arguments[0].click();", city_link)
                        
                        print(f"✓ {city_name} seçildi")
                        
                        # Close dropdown
                        try:
                            self.driver.execute_script("document.elementFromPoint(10, 10).click();")
                        except:
                            pass
                        self.random_medium_wait()  # Stealth
                        return True
                except:
                    continue
            
            print(f"✗ {city_name} bulunamadı")
            return False
            
        except Exception as e:
            logger.error(f"Error selecting city {city_name}: {e}")
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
        """Get total number of pages"""
        try:
            pagination_selectors = self.common_selectors.get("pagination", [])
            
            for selector in pagination_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        last_href = elements[-1].get_attribute("href")
                        if last_href:
                            match = re.search(r"page=(\d+)", last_href)
                            if match:
                                return int(match.group(1))
                except:
                    continue
            
            return 1
        except:
            return 1
    
    def scrape_city(self, city: str, max_pages: int = None, api_mode: bool = False, progress_callback=None) -> List[Dict[str, Any]]:
        """Scrape all listings for a single city"""
        print(f"\n{'=' * 60}")
        print(f"{city} İÇİN SCRAPING BAŞLIYOR")
        print("=" * 60)
        
        if progress_callback:
            progress_callback(f"{city} için tarama başlatılıyor...", current=0, total=100)
            
        try:
            # Select city
            if not self.select_single_city(city):
                print(f"{city} seçilemedi, atlanıyor...")
                return []
            
            # Search
            if not self.search_listings():
                print(f"{city} için arama yapılamadı")
                return []
            
            # Check for zero results
            try:
                zero_check = self.driver.find_elements(
                    By.XPATH, "//span[contains(text(), 'için 0 ilan bulundu')]"
                )
                if zero_check:
                    print(f"⚠️  {city} için 0 ilan bulundu")
                    return []
            except:
                pass
            
            # Get total pages
            total_pages = self.get_total_pages()
            print(f"{city} için toplam {total_pages} sayfa mevcut")
            
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
                print(f"{city} - Sayfa {page}/{pages_to_scrape}...")
                
                if progress_callback:
                    page_progress = int((page / pages_to_scrape) * 100)
                    progress_callback(f"{city} - Sayfa {page}/{pages_to_scrape} taranıyor...", current=page, total=pages_to_scrape, progress=page_progress)
                
                if page > 1:
                    page_url = f"{self.base_url}?page={page}"
                    self.driver.get(page_url)
                    self.random_long_wait()  # Stealth: sayfa geçişi
                    self.wait_for_element(self.common_selectors.get("listing_results"))
                
                page_listings = self.scrape_current_page()
                city_listings.extend(page_listings)
                
                print(f"   Sayfa {page}: {len(page_listings)} ilan")
                
                if page < pages_to_scrape:
                    self.random_medium_wait()  # Stealth: sayfalar arası
            
            print(f"✓ {city}: {len(city_listings)} ilan bulundu")
            return city_listings
            
        except Exception as e:
            logger.error(f"Error scraping {city}: {e}")
            return []
    
    def scrape_current_page(self) -> List[Dict[str, Any]]:
        """Scrape all listings on current page"""
        listings = []
        
        try:
            container_sel = self.common_selectors.get("listing_container")
            self.wait_for_element(self.common_selectors.get("listing_results"))
            
            elements = self.driver.find_elements(By.CSS_SELECTOR, container_sel)
            print(f"Bulunan ilan: {len(elements)}")
            
            for element in elements:
                try:
                    data = self.parser.extract_listing_data(element)
                    if data:
                        listings.append(data)
                    time.sleep(random.uniform(0.02, 0.08))  # Stealth: mikro-rastgele
                except Exception as e:
                    continue
            
            print(f"İşlenen ilan: {len(listings)}")
            
        except Exception as e:
            logger.error(f"Page scrape error: {e}")
        
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
            for city in self.selected_cities:
                # We can control max pages via self.scrape_city if we modify it to accept max_pages argument
                # Currently scrape_city asks for input call: user_input = input(...)
                
                # We need to refactor scrape_city to take max_pages arg
                city_listings = self.scrape_city(city, max_pages=max_pages, api_mode=True, progress_callback=progress_callback)
                if city_listings:
                    all_results[city] = city_listings
                self.random_medium_wait()  # Stealth: şehirler arası
            
            # Save data
            if all_results:
                self.exporter.save_by_city(
                    all_results,
                    prefix=f"hepsiemlak_{self.listing_type}_{self.category}",
                    format="excel"
                )
                
                total = sum(len(v) for v in all_results.values())
                print(f"\n🎉 TOPLAM: {len(all_results)} şehir, {total} ilan")
            else:
                print("❌ Hiç ilan bulunamadı!")
                
        except Exception as e:
            logger.error(f"API scraping error: {e}")
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
                    prefix=f"hepsiemlak_{self.listing_type}_{self.category}",
                    format="excel"
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
                    prefix=f"hepsiemlak_{self.listing_type}_{self.category}_partial",
                    format="excel"
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
