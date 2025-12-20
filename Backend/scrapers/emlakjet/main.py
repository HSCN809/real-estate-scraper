# -*- coding: utf-8 -*-
"""
EmlakJet Main Scraper
Refactored from original emlakjet_main.py
"""

import time
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
        selected_locations: Optional[Dict] = None
    ):
        super().__init__(driver, base_url, "emlakjet", category, selected_locations)
        
        self.emlakjet_config = get_emlakjet_config()
        # Output: Outputs/EmlakJet Output/{category}/
        self.exporter = DataExporter(output_dir=f"Outputs/EmlakJet Output/{category}")
        
        # Initialize the appropriate parser
        parser_class = self.CATEGORY_PARSERS.get(category, KonutParser)
        self.parser = parser_class()
    
    def extract_listing_data(self, container) -> Optional[Dict[str, Any]]:
        """Use the category parser to extract listing data"""
        return self.parser.extract_listing_data(container)
    
    def parse_category_details(self, quick_info: str, title: str) -> Dict[str, Any]:
        """Use the category parser to parse details"""
        return self.parser.parse_category_details(quick_info, title)
    
    def get_location_options(self, location_type: str, current_url: str) -> List[Dict]:
        """Get location options (il, ilçe, mahalle) from current page"""
        try:
            logger.info(f"Getting {location_type} options...")
            
            self.driver.get(current_url)
            time.sleep(3)
            
            location_options = []
            location_selector = self.common_selectors.get("location_links")
            
            location_links = self.driver.find_elements(By.CSS_SELECTOR, location_selector)
            
            for link in location_links:
                try:
                    location_name = link.text.strip()
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
                time.sleep(2)
            
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
            time.sleep(2)
            
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
             # In API mode default to ALL neighborhoods for now if district selected
             # Ideally we could filter by neighborhood list too
             return [district] # For speed in API mode maybe skip neighborhood drill down or scrape district root?
             # Let's return district root to scrape all listings in district
        
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
    
    def start_scraping_api(self, cities: Optional[List[str]] = None, districts: Optional[List[str]] = None, max_pages: int = 1, progress_callback=None):
        """API entry point for scraping without user interaction"""
        print(f"\n🚀 API: EmlakJet {self.category.capitalize()} Scraper başlatılıyor")
        
        if progress_callback:
            progress_callback(f"{self.category.capitalize()} taraması başlatılıyor...", 0, 100, 0)
        
        try:
            # Map city names to indices if possible, or search logic?
            # Existing select_provinces logic is index based on scraping "all cities" list.
            # We need to find indices matching names.
            
            print("Getting province list...")
            all_provinces = self.get_location_options("İller", self.base_url)
            
            api_indices = []
            if cities:
                for idx, p in enumerate(all_provinces, 1):
                     if p['name'] in cities:
                         api_indices.append(idx)
            
            # Step 1: Select provinces
            provinces = self.select_provinces(api_indices=api_indices if cities else None) 
            # If no cities provided, maybe scraping all is too much?
            # For safety, if no cities, return or error? 
            # In select_provinces logic above, if api_indices is None (but arg passed), it asks user? 
            # No, we modified it to check `if api_indices:`
            if not provinces and not cities:
                 # If cities empty and api call, maybe we shouldn't ask user.
                 logger.error("No cities provided for API scrape")
                 return
            
            user_max_pages = max_pages
            
            # Step 2: Process each province sequentially
            for prov_idx, province in enumerate(provinces, 1):
                # Get listing count for this province
                listing_count = self.get_listing_count(province['url'])
                
                print("\n" + "=" * 70)
                print(f"🏙️  İL {prov_idx}/{len(provinces)}: {province['name']} (Toplam İlan: {listing_count})")
                print("=" * 70)
                
                if progress_callback:
                    base_progress = ((prov_idx - 1) / len(provinces)) * 100
                    progress_callback(f"İşleniyor: {province['name']}...", prov_idx, len(provinces), base_progress)
                
                # Select districts for this province
                # We pass api_mode=True
                selected_districts, process_neighborhoods = self.select_districts_for_province(
                    province, 
                    api_mode=True, 
                    api_districts=districts
                )
                
                if not selected_districts:
                    print(f"⏭️  {province['name']} atlandı.")
                    continue
                
                # Process each district
                for dist_idx, district in enumerate(selected_districts, 1):
                    # Check if this is province-level (no district selection)
                    if district.get('url') == province.get('url'):
                        # Scrape entire province directly
                        targets = [{'url': province['url'], 'label': province['name'], 'type': 'il'}]
                    elif process_neighborhoods:
                        # Select neighborhoods for this district
                        # api_mode=True returns just district root usually
                        print(f"\n📍 İlçe {dist_idx}/{len(selected_districts)}: {district['name']}")
                        neighborhoods = self.select_neighborhoods_for_district(district, api_mode=True)
                        if not neighborhoods:
                            continue
                        
                        # Check if district-level or neighborhood-level
                        if len(neighborhoods) == 1 and neighborhoods[0].get('url') == district.get('url'):
                            targets = [{'url': district['url'], 'label': f"{district.get('il', '')} / {district['name']}", 'type': 'ilce'}]
                        else:
                            targets = [{'url': n['url'], 'label': f"{n.get('il', '')} / {n.get('ilce', '')} / {n['name']}", 'type': 'mahalle'} for n in neighborhoods]
                    else:
                        # Scrape district directly without neighborhood selection
                        targets = [{'url': district['url'], 'label': f"{district.get('il', '')} / {district['name']}", 'type': 'ilce'}]
                    
                    # Scrape targets
                    for target in targets:
                        print(f"\n📍 Taranıyor: {target['label']}")
                        
                        url_max_pages = self.get_max_pages(target['url'])
                        max_pages_to_scrape = min(user_max_pages, url_max_pages)
                        print(f"📊 {url_max_pages} sayfa mevcut, {max_pages_to_scrape} sayfa taranacak.")
                        
                        should_skip = self.scrape_pages(target['url'], max_pages_to_scrape)
                        
                        if progress_callback:
                            # Refine progress based on district progress
                            pass

                        if should_skip:
                            print("⏭️  Bu lokasyon atlandı.")
            
            # Save data (only Excel)
            if self.all_listings:
                self.exporter.save_excel(
                    self.all_listings,
                    prefix=f"emlakjet_{self.category}_ilanlari"
                )
                print(f"\n✅ Scraping tamamlandı! Toplam {len(self.all_listings)} ilan bulundu.")
            else:
                print("\n❌ Hiç ilan bulunamadı!")

        except Exception as e:
            logger.error(f"API Scraping error: {e}")
            raise e

    def start_scraping(self):
        """Main scraping entry point - Sequential city processing"""
        print(f"\n🚀 EmlakJet {self.category.capitalize()} Scraper başlatılıyor")
        
        try:
            # Step 1: Select provinces
            provinces = self.select_provinces()
            if not provinces:
                print("❌ İl seçilmedi!")
                return
            
            # Get page count from user (applies to all)
            user_max_pages = self.get_user_page_count()
            if user_max_pages is None:
                return
            
            # Step 2: Process each province sequentially
            for prov_idx, province in enumerate(provinces, 1):
                # Get listing count for this province
                listing_count = self.get_listing_count(province['url'])
                
                print("\n" + "=" * 70)
                print(f"🏙️  İL {prov_idx}/{len(provinces)}: {province['name']} (Toplam İlan: {listing_count})")
                print("=" * 70)
                
                # Select districts for this province
                districts, process_neighborhoods = self.select_districts_for_province(province)
                if not districts:
                    print(f"⏭️  {province['name']} atlandı.")
                    continue
                
                # Process each district
                for dist_idx, district in enumerate(districts, 1):
                    # Check if this is province-level (no district selection)
                    if district.get('url') == province.get('url'):
                        # Scrape entire province directly
                        targets = [{'url': province['url'], 'label': province['name'], 'type': 'il'}]
                    elif process_neighborhoods:
                        # Select neighborhoods for this district
                        print(f"\n📍 İlçe {dist_idx}/{len(districts)}: {district['name']}")
                        neighborhoods = self.select_neighborhoods_for_district(district)
                        if not neighborhoods:
                            continue
                        
                        # Check if district-level or neighborhood-level
                        if len(neighborhoods) == 1 and neighborhoods[0].get('url') == district.get('url'):
                            targets = [{'url': district['url'], 'label': f"{district.get('il', '')} / {district['name']}", 'type': 'ilce'}]
                        else:
                            targets = [{'url': n['url'], 'label': f"{n.get('il', '')} / {n.get('ilce', '')} / {n['name']}", 'type': 'mahalle'} for n in neighborhoods]
                    else:
                        # Scrape district directly without neighborhood selection
                        targets = [{'url': district['url'], 'label': f"{district.get('il', '')} / {district['name']}", 'type': 'ilce'}]
                    
                    # Scrape targets
                    for target in targets:
                        print(f"\n📍 Taranıyor: {target['label']}")
                        
                        url_max_pages = self.get_max_pages(target['url'])
                        max_pages = min(user_max_pages, url_max_pages)
                        print(f"📊 {url_max_pages} sayfa mevcut, {max_pages} sayfa taranacak.")
                        
                        should_skip = self.scrape_pages(target['url'], max_pages)
                        if should_skip:
                            print("⏭️  Bu lokasyon atlandı.")
            
            # Save data (only Excel)
            if self.all_listings:
                self.exporter.save_excel(
                    self.all_listings,
                    prefix=f"emlakjet_{self.category}_ilanlari"
                )
                print(f"\n✅ Scraping tamamlandı! Toplam {len(self.all_listings)} ilan bulundu.")
            else:
                print("\n❌ Hiç ilan bulunamadı!")
            
        except KeyboardInterrupt:
            print("\n⏹️  İşlem kullanıcı tarafından iptal edildi.")
            if self.all_listings:
                self.exporter.save_excel(self.all_listings, prefix=f"emlakjet_{self.category}_partial")
                print(f"💾 {len(self.all_listings)} ilan kaydedildi.")
        except Exception as e:
            logger.error(f"Scraping error: {e}")
            print(f"❌ Scraping sırasında hata: {e}")


def main():
    """Main entry point for EmlakJet scraper"""
    print("\n" + "=" * 60)
    print("🏠 EMLAKJET SCRAPER")
    print("=" * 60)
    
    # Category selection
    categories = ['konut', 'arsa', 'isyeri', 'turistik_tesis']
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
        
        config = get_emlakjet_config()
        base_url = config.base_url + config.categories['satilik'].get(category, '')
        
        scraper = EmlakJetScraper(driver, base_url, category)
        scraper.start_scraping()
        
    except Exception as e:
        logger.error(f"Error: {e}")
        print(f"❌ Hata: {e}")
    
    finally:
        manager.stop()


if __name__ == "__main__":
    main()
