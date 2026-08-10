# -*- coding: utf-8 -*-
"""Tüm scraper'lar için ortak işlevsellik sağlayan temel sınıf - gizli mod"""

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
    StaleElementReferenceException,
)

from .config import get_config
from .selectors import get_selectors, get_common_selectors

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """Tüm scraper'lar için temel sınıf"""

    def __init__(
        self,
        driver: WebDriver,
        base_url: str,
        platform: str,
        category: str,
        selected_locations: Optional[Dict] = None,
    ):
        """Scraper'ı başlat"""
        self.driver = driver
        self.base_url = base_url
        self.platform = platform
        self.category = category
        self.config = get_config()

        # Platform/kategori seçicilerini yükle
        self.selectors = get_selectors(platform, category)
        self.common_selectors = get_common_selectors(platform)

        # Lokasyon seçimi
        self.selected_locations = selected_locations or {
            "iller": [],
            "ilceler": [],
            "mahalleler": [],
        }

        # Veri deposu
        self.all_listings: List[Dict[str, Any]] = []

        # Bekleme nesnesi
        self.wait = WebDriverWait(driver, self.config.element_wait_timeout)

    # =========================================================================
    # Gizli bekleme metotları
    # =========================================================================

    def random_wait(self, wait_type: str = "medium") -> float:
        """Bot tespitinden kaçınmak için rastgele bekleme"""
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
    # Alt sınıflar tarafından uygulanması gereken metotlar

    @abstractmethod
    def extract_listing_data(self, container: WebElement) -> Optional[Dict[str, Any]]:
        """Tek bir ilan elementinden veri çıkar"""
        pass

    @abstractmethod
    def parse_category_details(self, quick_info: str, title: str) -> Dict[str, Any]:
        """Kategori detaylarını parse et"""
        pass

    # =========================================================================
    # Ortak element çıkarma metotları
    # =========================================================================

    def get_element_text(self, container: WebElement, selector: str) -> str:
        """Elementten güvenli şekilde metin al"""
        try:
            element = container.find_element(By.CSS_SELECTOR, selector)
            return element.text.strip()
        except (NoSuchElementException, StaleElementReferenceException):
            return ""

    def get_element_attribute(
        self, container: WebElement, selector: str, attribute: str
    ) -> str:
        """Elementten güvenli şekilde attribute al"""
        try:
            element = container.find_element(By.CSS_SELECTOR, selector)
            return element.get_attribute(attribute) or ""
        except (NoSuchElementException, StaleElementReferenceException):
            return ""

    def find_elements_safe(self, selector: str) -> List[WebElement]:
        """Element listesini güvenli şekilde bul"""
        try:
            return self.driver.find_elements(By.CSS_SELECTOR, selector)
        except Exception as e:
            logger.warning(f"Failed to find elements with selector '{selector}': {e}")
            return []

    def wait_for_element(
        self, selector: str, timeout: Optional[int] = None
    ) -> Optional[WebElement]:
        """Elementin sayfada görünmesini bekle"""
        try:
            wait = WebDriverWait(
                self.driver, timeout or self.config.element_wait_timeout
            )
            return wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
            )
        except TimeoutException:
            logger.warning(f"Timeout waiting for element: {selector}")
            return None

    def wait_for_clickable(
        self, selector: str, timeout: Optional[int] = None
    ) -> Optional[WebElement]:
        """Elementin tıklanabilir olmasını bekle"""
        try:
            wait = WebDriverWait(
                self.driver, timeout or self.config.element_wait_timeout
            )
            return wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
        except TimeoutException:
            logger.warning(f"Timeout waiting for clickable element: {selector}")
            return None

    # =========================================================================
    # Kullanıcı girdi metotları
    # =========================================================================

    def get_user_choice(self, max_option: int) -> Optional[int]:
        """Kullanıcıdan tek seçim al"""
        try:
            user_input = input(f"\nSeçiminiz (1-{max_option}): ").strip()

            # Çoklu seçim işaretleyicilerini kontrol et
            if any(char in user_input for char in [",", " ", "-"]):
                return None

            choice = int(user_input)
            if 1 <= choice <= max_option:
                return choice
            else:
                print(
                    f"❌ Geçersiz seçim! Lütfen 1-{max_option} arasında bir sayı girin."
                )
                return None
        except ValueError:
            print("❌ Geçersiz giriş! Lütfen bir sayı girin.")
            return None

    def get_user_page_count(self) -> Optional[int]:
        """Kullanıcıdan sayfa sayısı al"""
        max_pages = self.config.max_pages_per_location

        while True:
            try:
                user_input = input(
                    f"\n🔢 Kaç sayfa scrape edilecek? (1-{max_pages}): "
                ).strip()

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
        self, items: List[Dict], selected_items: List[Dict], item_type: str
    ) -> None:
        """Çoklu seçim menüsü"""
        print(f"\n🎯 ÇOKLU {item_type.upper()} SEÇİMİ")
        print(
            "Birden fazla seçim yapmak için numaraları virgülle veya boşlukla ayırarak girin."
        )
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
        """Çoklu seçim girdisini parse et"""
        selections: Set[int] = set()

        # Virgülle ayrılmış
        if "," in user_input:
            parts = user_input.split(",")
        # Boşlukla ayrılmış
        elif " " in user_input:
            parts = user_input.split()
        # Sadece aralık
        elif "-" in user_input and user_input.count("-") == 1:
            try:
                start, end = map(int, user_input.split("-"))
                if 1 <= start <= end <= max_value:
                    return list(range(start, end + 1))
            except ValueError:
                pass
            return []
        # Tek sayı
        else:
            if user_input.isdigit():
                num = int(user_input)
                if 1 <= num <= max_value:
                    return [num]
            return []

        # Parçaları işle
        for part in parts:
            part = part.strip()
            if "-" in part:
                try:
                    range_parts = part.split("-")
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
    # Görüntüleme metotları
    # =========================================================================

    def display_menu(
        self,
        title: str,
        items: List,
        show_back: bool = True,
        show_exit: bool = True,
        selected_items: Optional[List] = None,
    ) -> int:
        """Menü görüntüle ve sonraki seçenek numarasını döndür"""
        print("\n" + "=" * 50)
        print(f"🎯 {title}")
        print("=" * 50)

        # Seçili öğe isimlerinin kümesini oluştur
        selected_names: Set[str] = set()
        if selected_items:
            for item in selected_items:
                if isinstance(item, dict) and "name" in item:
                    selected_names.add(item["name"])
                elif isinstance(item, str):
                    selected_names.add(item)

        # 12'den fazla öğe varsa 4 sütun halinde göster
        if len(items) > 12:
            cols = 4
            col_width = 20
            for i in range(0, len(items), cols):
                row = ""
                for j in range(cols):
                    idx = i + j
                    if idx < len(items):
                        item = items[idx]
                        if isinstance(item, dict) and "name" in item:
                            display_name = item["name"][: col_width - 6]
                        else:
                            display_name = str(item)[: col_width - 6]

                        is_selected = display_name in selected_names
                        mark = "✓" if is_selected else " "
                        row += f"{idx + 1:2d}.{mark}{display_name:<{col_width - 5}}"
                print(row)
        else:
            # Küçük listeler için tek sütun halinde göster
            for i, item in enumerate(items, 1):
                is_selected = False

                if isinstance(item, dict) and "name" in item:
                    display_name = item["name"]
                    is_selected = display_name in selected_names

                    # Varsa ilan sayısını göster
                    if "ad_count" in item and item["ad_count"] != "0":
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
        """Seçili lokasyonları görüntüle"""
        if any(self.selected_locations.values()):
            print("\n📍 SEÇİLİ LOKASYONLAR:")
            if self.selected_locations["iller"]:
                names = [il["name"] for il in self.selected_locations["iller"]]
                print(f"   🏙️  İller: {', '.join(names)}")
            if self.selected_locations["ilceler"]:
                names = [
                    f"{ilce.get('il', '')}-{ilce['name']}"
                    for ilce in self.selected_locations["ilceler"]
                ]
                print(f"   🏘️  İlçeler: {', '.join(names)}")
            if self.selected_locations["mahalleler"]:
                names = [mah["name"] for mah in self.selected_locations["mahalleler"]]
                print(f"   🏡 Mahalleler: {', '.join(names)}")
        else:
            print("\n📍 SEÇİLİ LOKASYONLAR: Henüz lokasyon seçilmedi")

    # =========================================================================
    # Navigasyon metotları
    # =========================================================================

    def navigate_to(self, url: str, wait_time: Optional[float] = None) -> bool:
        """Belirtilen URL'ye git"""
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
        """Mevcut maksimum sayfa sayısını al"""
        return 1

    # =========================================================================
    # Tarama metotları
    # =========================================================================

    def scrape_current_page(self) -> List[Dict[str, Any]]:
        """Mevcut sayfadaki tüm ilanları tara"""
        listings = []

        try:
            container_selector = self.common_selectors.get("listing_container")
            if not container_selector:
                logger.error("No listing_container selector defined")
                return []

            containers = self.find_elements_safe(container_selector)
            logger.info(f"Found {len(containers)} listing containers")

            # EmlakJet: "Benzer İlanlar" section'ındaki kartları hariç tut
            if self.platform == "emlakjet" and containers:
                filtered = []
                for c in containers:
                    try:
                        # Kartın "similarListingWrapper" veya "similarlisting" parent'ı varsa hariç tut
                        is_similar = self.driver.execute_script(
                            'return arguments[0].closest(\'[class*="similarListing"], [class*="similarlisting"]\') !== null;',
                            c,
                        )
                        if not is_similar:
                            filtered.append(c)
                    except Exception:
                        filtered.append(c)
                if len(filtered) < len(containers):
                    logger.info(
                        f"Filtered out {len(containers) - len(filtered)} 'Benzer İlanlar' listings"
                    )
                containers = filtered

            for container in containers:
                try:
                    data = self.extract_listing_data(container)
                    if data:
                        data["tarih"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        listings.append(data)
                except Exception as e:
                    logger.warning(f"Failed to extract listing: {e}")
                    continue

        except Exception as e:
            logger.error(f"Failed to scrape page: {e}")

        return listings

    def scrape_pages(
        self, target_url: str, max_pages: int, on_page_scraped=None
    ) -> bool:
        """Birden fazla sayfayı tara"""
        first_page_count = 0

        for current_page in range(1, max_pages + 1):
            # Durdurma kontrolü
            if (
                hasattr(self, "_stop_checker")
                and self._stop_checker
                and self._stop_checker()
            ):
                logger.info("Stop requested, ending page scraping")
                break

            # İlan limiti kontrolü
            if (
                hasattr(self, "_max_listings")
                and self._max_listings > 0
                and len(self.all_listings) >= self._max_listings
            ):
                logger.info(
                    f"Listing limit reached ({self._max_listings}), ending page scraping"
                )
                break

            print(f"\n🔍 Sayfa {current_page} taranıyor...")

            try:
                # Sayfa URL'sini oluştur
                if current_page > 1:
                    separator = "&" if "?" in target_url else "?"
                    page_url = f"{target_url}{separator}sayfa={current_page}"
                else:
                    page_url = target_url

                self.driver.get(page_url)
                time.sleep(self.config.wait_between_pages)

                # Sıfır ilan kontrolü (EmlakJet)
                if current_page == 1:
                    try:
                        no_results = self.driver.find_elements(
                            By.CSS_SELECTOR, "span.styles_title__e_y3h"
                        )
                        for element in no_results:
                            if "ilan bulunamadı" in element.text.lower():
                                print("⚠️  Bu lokasyonda ilan bulunamadı, atlanıyor...")
                                return True
                    except Exception:
                        pass

                # Sayfayı tara
                listings = self.scrape_current_page()
                self.all_listings.extend(listings)

                # Her sayfa sonrası callback (DB'ye anında kaydetme için)
                if on_page_scraped and listings:
                    on_page_scraped(listings)

                if current_page == 1:
                    first_page_count = len(listings)

                print(f"   ✅ Sayfa {current_page}: {len(listings)} ilan bulundu")

            except Exception as e:
                logger.error(f"Error scraping page {current_page}: {e}")
                print(f"   ❌ Sayfa {current_page} taranırken hata: {e}")
                continue

        # İlk sayfada ilan yoksa atla
        return first_page_count == 0 and max_pages == 1
