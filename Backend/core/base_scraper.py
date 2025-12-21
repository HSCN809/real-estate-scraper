# -*- coding: utf-8 -*-
"""
Base Scraper class with common functionality for all scrapers
STEALTH MODE - Randomized delays to avoid bot detection
"""

import time
import random
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Set
from datetime import datetime

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    StaleElementReferenceException
)

from .config import get_config
from .selectors import get_selectors, get_common_selectors

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """
    Base class for all scrapers.
    Provides common functionality like user input, navigation, and element extraction.
    """
    
    def __init__(
        self,
        driver: WebDriver,
        base_url: str,
        platform: str,
        category: str,
        selected_locations: Optional[Dict] = None
    ):
        """
        Initialize the scraper.
        
        Args:
            driver: Selenium WebDriver instance
            base_url: Base URL for scraping
            platform: Platform name ('emlakjet' or 'hepsiemlak')
            category: Category name ('konut', 'arsa', etc.)
            selected_locations: Pre-selected locations
        """
        self.driver = driver
        self.base_url = base_url
        self.platform = platform
        self.category = category
        self.config = get_config()
        
        # Load selectors for this platform/category
        self.selectors = get_selectors(platform, category)
        self.common_selectors = get_common_selectors(platform)
        
        # Location selection
        self.selected_locations = selected_locations or {
            'iller': [],
            'ilceler': [],
            'mahalleler': []
        }
        
        # Data storage
        self.all_listings: List[Dict[str, Any]] = []
        
        # Wait object
        self.wait = WebDriverWait(driver, self.config.element_wait_timeout)
    
    # =========================================================================
    # STEALTH WAIT METHODS - Rastgele bekleme süreleri
    # =========================================================================
    
    def random_wait(self, wait_type: str = "medium") -> float:
        """
        Rastgele bekleme süresi - bot tespitinden kaçınmak için.
        
        Args:
            wait_type: "short", "medium", or "long"
            
        Returns:
            Beklenen süre (saniye)
        """
        if wait_type == "short":
            min_wait, max_wait = self.config.random_wait_short
        elif wait_type == "long":
            min_wait, max_wait = self.config.random_wait_long
        else:  # medium (default)
            min_wait, max_wait = self.config.random_wait_medium
        
        wait_time = random.uniform(min_wait, max_wait)
        time.sleep(wait_time)
        return wait_time
    
    def random_short_wait(self) -> float:
        """Kısa rastgele bekleme (0.5-1.5 sn)"""
        return self.random_wait("short")
    
    def random_medium_wait(self) -> float:
        """Orta rastgele bekleme (1.0-2.5 sn)"""
        return self.random_wait("medium")
    
    def random_long_wait(self) -> float:
        """Uzun rastgele bekleme (2.0-4.0 sn)"""
        return self.random_wait("long")
    
    # =========================================================================
    # ABSTRACT METHODS (must be implemented by subclasses)
    
    @abstractmethod
    def extract_listing_data(self, container: WebElement) -> Optional[Dict[str, Any]]:
        """
        Extract data from a single listing element.
        Must be implemented by each category parser.
        
        Args:
            container: WebElement containing the listing
            
        Returns:
            Dictionary with listing data or None if extraction failed
        """
        pass
    
    @abstractmethod
    def parse_category_details(self, quick_info: str, title: str) -> Dict[str, Any]:
        """
        Parse category-specific details from quick info and title.
        Must be implemented by each category parser.
        
        Args:
            quick_info: Quick info text from listing
            title: Title text from listing
            
        Returns:
            Dictionary with parsed details
        """
        pass
    
    # =========================================================================
    # COMMON ELEMENT EXTRACTION
    # =========================================================================
    
    def get_element_text(self, container: WebElement, selector: str) -> str:
        """Safely get text from an element"""
        try:
            element = container.find_element(By.CSS_SELECTOR, selector)
            return element.text.strip()
        except (NoSuchElementException, StaleElementReferenceException):
            return ""
    
    def get_element_attribute(
        self,
        container: WebElement,
        selector: str,
        attribute: str
    ) -> str:
        """Safely get attribute from an element"""
        try:
            element = container.find_element(By.CSS_SELECTOR, selector)
            return element.get_attribute(attribute) or ""
        except (NoSuchElementException, StaleElementReferenceException):
            return ""
    
    def find_elements_safe(self, selector: str) -> List[WebElement]:
        """Safely find elements with logging"""
        try:
            return self.driver.find_elements(By.CSS_SELECTOR, selector)
        except Exception as e:
            logger.warning(f"Failed to find elements with selector '{selector}': {e}")
            return []
    
    def wait_for_element(self, selector: str, timeout: Optional[int] = None) -> Optional[WebElement]:
        """Wait for element to be present"""
        try:
            wait = WebDriverWait(self.driver, timeout or self.config.element_wait_timeout)
            return wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
        except TimeoutException:
            logger.warning(f"Timeout waiting for element: {selector}")
            return None
    
    def wait_for_clickable(self, selector: str, timeout: Optional[int] = None) -> Optional[WebElement]:
        """Wait for element to be clickable"""
        try:
            wait = WebDriverWait(self.driver, timeout or self.config.element_wait_timeout)
            return wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
        except TimeoutException:
            logger.warning(f"Timeout waiting for clickable element: {selector}")
            return None
    
    # =========================================================================
    # USER INPUT METHODS
    # =========================================================================
    
    def get_user_choice(self, max_option: int) -> Optional[int]:
        """
        Get a single choice from user.
        
        Args:
            max_option: Maximum valid option number
            
        Returns:
            User's choice or None if invalid
        """
        try:
            user_input = input(f"\nSeçiminiz (1-{max_option}): ").strip()
            
            # Check for multiple selection markers
            if any(char in user_input for char in [',', ' ', '-']):
                return None
            
            choice = int(user_input)
            if 1 <= choice <= max_option:
                return choice
            else:
                print(f"❌ Geçersiz seçim! Lütfen 1-{max_option} arasında bir sayı girin.")
                return None
        except ValueError:
            print("❌ Geçersiz giriş! Lütfen bir sayı girin.")
            return None
    
    def get_user_page_count(self) -> Optional[int]:
        """Get number of pages to scrape from user"""
        max_pages = self.config.max_pages_per_location
        
        while True:
            try:
                user_input = input(f"\n🔢 Kaç sayfa scrape edilecek? (1-{max_pages}): ").strip()
                
                if not user_input:
                    print("❌ Geçersiz giriş! Lütfen bir sayı girin.")
                    continue
                
                page_count = int(user_input)
                
                if page_count < 1:
                    print("❌ En az 1 sayfa seçmelisiniz!")
                    continue
                
                if page_count > max_pages:
                    print(f"❌ Maksimum {max_pages} sayfa seçebilirsiniz!")
                    continue
                
                print(f"✅ {page_count} sayfa scrape edilecek.")
                return page_count
                
            except ValueError:
                print("❌ Geçersiz giriş! Lütfen bir sayı girin.")
            except KeyboardInterrupt:
                print("\n⏹️  İşlem kullanıcı tarafından iptal edildi.")
                return None
    
    def multiple_selection_menu(
        self,
        items: List[Dict],
        selected_items: List[Dict],
        item_type: str
    ) -> None:
        """
        Handle multiple selection from a list.
        
        Args:
            items: List of items to select from
            selected_items: List to store selected items (modified in place)
            item_type: Type name for display (e.g., 'il', 'ilçe')
        """
        print(f"\n🎯 ÇOKLU {item_type.upper()} SEÇİMİ")
        print("Birden fazla seçim yapmak için numaraları virgülle veya boşlukla ayırarak girin.")
        print("Örnek: 1,3,5 veya 1 3 5 veya 1-5")
        
        while True:
            try:
                user_input = input(f"\nSeçimlerinizi girin (1-{len(items)}): ").strip()
                
                if not user_input:
                    print("❌ Boş giriş! Lütfen numara girin.")
                    continue
                
                selections = self._parse_selection_input(user_input, len(items))
                
                if selections:
                    selected_items.clear()
                    for selection in selections:
                        selected_items.append(items[selection - 1])
                    
                    print(f"✅ {len(selections)} {item_type} seçildi:")
                    for selection in selections:
                        print(f"   - {items[selection - 1].get('name', 'Unknown')}")
                    return
                else:
                    print("❌ Geçerli seçim bulunamadı!")
                    
            except ValueError:
                print("❌ Geçersiz giriş! Lütfen numara girin.")
            except Exception as e:
                print(f"❌ Hata: {e}")
    
    def _parse_selection_input(self, user_input: str, max_value: int) -> List[int]:
        """Parse user input for multiple selection"""
        selections: Set[int] = set()
        
        # Handle comma-separated
        if ',' in user_input:
            parts = user_input.split(',')
        # Handle space-separated
        elif ' ' in user_input:
            parts = user_input.split()
        # Handle range only
        elif '-' in user_input and user_input.count('-') == 1:
            try:
                start, end = map(int, user_input.split('-'))
                if 1 <= start <= end <= max_value:
                    return list(range(start, end + 1))
            except ValueError:
                pass
            return []
        # Single number
        else:
            if user_input.isdigit():
                num = int(user_input)
                if 1 <= num <= max_value:
                    return [num]
            return []
        
        # Process parts
        for part in parts:
            part = part.strip()
            if '-' in part:
                try:
                    range_parts = part.split('-')
                    if len(range_parts) == 2:
                        start = int(range_parts[0].strip())
                        end = int(range_parts[1].strip())
                        for i in range(start, end + 1):
                            if 1 <= i <= max_value:
                                selections.add(i)
                except ValueError:
                    continue
            elif part.isdigit():
                num = int(part)
                if 1 <= num <= max_value:
                    selections.add(num)
        
        return sorted(list(selections))
    
    # =========================================================================
    # DISPLAY METHODS
    # =========================================================================
    
    def display_menu(
        self,
        title: str,
        items: List,
        show_back: bool = True,
        show_exit: bool = True,
        selected_items: Optional[List] = None
    ) -> int:
        """
        Display a menu and return the next option number.
        
        Args:
            title: Menu title
            items: List of items (strings or dicts with 'name' key)
            show_back: Whether to show back option
            show_exit: Whether to show exit option
            selected_items: List of already selected items
            
        Returns:
            Next available option number
        """
        print(f"\n" + "=" * 50)
        print(f"🎯 {title}")
        print("=" * 50)
        
        # Build set of selected item names
        selected_names: Set[str] = set()
        if selected_items:
            for item in selected_items:
                if isinstance(item, dict) and 'name' in item:
                    selected_names.add(item['name'])
                elif isinstance(item, str):
                    selected_names.add(item)
        
        # Display items in 4 columns if more than 12 items
        if len(items) > 12:
            cols = 4
            col_width = 20
            for i in range(0, len(items), cols):
                row = ""
                for j in range(cols):
                    idx = i + j
                    if idx < len(items):
                        item = items[idx]
                        if isinstance(item, dict) and 'name' in item:
                            display_name = item['name'][:col_width - 6]
                        else:
                            display_name = str(item)[:col_width - 6]
                        
                        is_selected = display_name in selected_names
                        mark = "✓" if is_selected else " "
                        row += f"{idx + 1:2d}.{mark}{display_name:<{col_width - 5}}"
                print(row)
        else:
            # Display items in single column for small lists
            for i, item in enumerate(items, 1):
                is_selected = False
                
                if isinstance(item, dict) and 'name' in item:
                    display_name = item['name']
                    is_selected = display_name in selected_names
                    
                    # Show ad count if available
                    if 'ad_count' in item and item['ad_count'] != "0":
                        display_name = f"{display_name} ({item['ad_count']})"
                else:
                    display_name = str(item)
                    is_selected = display_name in selected_names
                
                checkmark = " ✅" if is_selected else ""
                print(f"{i}. {display_name}{checkmark}")
        
        option_number = len(items) + 1
        
        if show_back:
            print(f"\n{option_number}. ↩️ Üst menüye dön")
            option_number += 1
        
        if show_exit:
            print(f"{option_number}. 🚪 Çıkış")
        
        return option_number
    
    def display_selected_locations(self) -> None:
        """Display currently selected locations"""
        if any(self.selected_locations.values()):
            print(f"\n📍 SEÇİLİ LOKASYONLAR:")
            if self.selected_locations['iller']:
                names = [il['name'] for il in self.selected_locations['iller']]
                print(f"   🏙️  İller: {', '.join(names)}")
            if self.selected_locations['ilceler']:
                names = [f"{ilce.get('il', '')}-{ilce['name']}" for ilce in self.selected_locations['ilceler']]
                print(f"   🏘️  İlçeler: {', '.join(names)}")
            if self.selected_locations['mahalleler']:
                names = [mah['name'] for mah in self.selected_locations['mahalleler']]
                print(f"   🏡 Mahalleler: {', '.join(names)}")
        else:
            print(f"\n📍 SEÇİLİ LOKASYONLAR: Henüz lokasyon seçilmedi")
    
    # =========================================================================
    # NAVIGATION METHODS
    # =========================================================================
    
    def navigate_to(self, url: str, wait_time: Optional[float] = None) -> bool:
        """
        Navigate to a URL.
        
        Args:
            url: URL to navigate to
            wait_time: Time to wait after navigation
            
        Returns:
            True if successful, False otherwise
        """
        try:
            wait = wait_time or self.config.wait_between_pages
            print(f"\n🌐 Sayfaya gidiliyor: {url}")
            self.driver.get(url)
            time.sleep(wait)
            print(f"✅ Başarılı! Geçerli URL: {self.driver.current_url}")
            return True
        except Exception as e:
            logger.error(f"Navigation failed: {e}")
            print(f"❌ Sayfaya gidilirken hata: {e}")
            return False
    
    def get_max_pages(self) -> int:
        """Get maximum number of pages available (to be overridden)"""
        return 1
    
    # =========================================================================
    # SCRAPING METHODS
    # =========================================================================
    
    def scrape_current_page(self) -> List[Dict[str, Any]]:
        """
        Scrape all listings on the current page.
        
        Returns:
            List of listing data dictionaries
        """
        listings = []
        
        try:
            container_selector = self.common_selectors.get("listing_container")
            if not container_selector:
                logger.error("No listing_container selector defined")
                return []
            
            containers = self.find_elements_safe(container_selector)
            logger.info(f"Found {len(containers)} listing containers")
            
            for container in containers:
                try:
                    data = self.extract_listing_data(container)
                    if data:
                        data['tarih'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        listings.append(data)
                except Exception as e:
                    logger.warning(f"Failed to extract listing: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"Failed to scrape page: {e}")
        
        return listings
    
    def scrape_pages(self, target_url: str, max_pages: int) -> bool:
        """
        Scrape multiple pages.
        
        Args:
            target_url: Base URL for scraping
            max_pages: Maximum number of pages to scrape
            
        Returns:
            True if should skip (no listings), False otherwise
        """
        first_page_count = 0
        
        for current_page in range(1, max_pages + 1):
            print(f"\n🔍 Sayfa {current_page} taranıyor...")
            
            try:
                # Construct page URL
                if current_page > 1:
                    separator = '&' if '?' in target_url else '?'
                    page_url = f"{target_url}{separator}sayfa={current_page}"
                else:
                    page_url = target_url
                
                self.driver.get(page_url)
                time.sleep(self.config.wait_between_pages)
                
                # Check for zero listings (EmlakJet)
                if current_page == 1:
                    try:
                        no_results = self.driver.find_elements(
                            By.CSS_SELECTOR, "span.styles_title__e_y3h"
                        )
                        for element in no_results:
                            if "ilan bulunamadı" in element.text.lower():
                                print("⚠️  Bu lokasyonda ilan bulunamadı, atlanıyor...")
                                return True
                    except:
                        pass
                
                # Scrape page
                listings = self.scrape_current_page()
                self.all_listings.extend(listings)
                
                if current_page == 1:
                    first_page_count = len(listings)
                
                print(f"   ✅ Sayfa {current_page}: {len(listings)} ilan bulundu")
                
            except Exception as e:
                logger.error(f"Error scraping page {current_page}: {e}")
                print(f"   ❌ Sayfa {current_page} taranırken hata: {e}")
                continue
        
        # Skip if no listings on first page
        return first_page_count == 0 and max_pages == 1
    
    # =========================================================================
    # MAIN SCRAPING FLOW
    # =========================================================================
    
    @abstractmethod
    def start_scraping(self) -> None:
        """
        Main scraping entry point.
        Must be implemented by each scraper.
        """
        pass
