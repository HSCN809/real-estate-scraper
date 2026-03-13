# -*- coding: utf-8 -*-
"""HepsiEmlak Ana Scraper - gizli mod"""

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
from core.failed_pages_tracker import FailedPagesTracker, FailedPageInfo, failed_pages_tracker
from utils.logger import get_logger, TaskLogLayout
from utils.data_exporter import DataExporter

from .parsers import KonutParser, ArsaParser, IsyeriParser, DevremulkParser, TuristikParser

logger = get_logger(__name__)
task_log = TaskLogLayout(logger)


def save_listings_to_db(db, listings: List[Dict], platform: str, kategori: str, ilan_tipi: str, alt_kategori: str = None, scrape_session_id: int = None):
    """İlan listesini veritabanına kaydet (upsert mantığı ile)"""
    if not db:
        return 0, 0, 0

    try:
        from database import crud
        new_count = 0
        updated_count = 0
        unchanged_count = 0

        for data in listings:
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
        logger.info(f"DB save: {new_count} new, {updated_count} updated, {unchanged_count} unchanged")
        return new_count, updated_count, unchanged_count
    except Exception as e:
        logger.error(f"DB save error: {e}")
        db.rollback()
        return 0, 0, 0


class HepsiemlakScraper(BaseScraper):
    """HepsiEmlak platformu ana scraper sınıfı"""
    
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
        self.total_new_listings = 0  # Global kümülatif yeni ilan sayacı

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

        # Veritabanı desteği (endpoints.py tarafından ayarlanır)
        self.db = None
        self.scrape_session_id = None
        self.total_scraped_count = 0
        self.new_listings_count = 0
        self.duplicate_count = 0

        # Uygun parser'ı başlat
        parser_class = self.CATEGORY_PARSERS.get(category, KonutParser)
        self.parser = parser_class()
    
    @property
    def subtype_name(self) -> Optional[str]:
        """Dosya adlandırma için subtype_path'inden alt kategori adını çıkar"""
        if self.subtype_path:
            # /satilik/daire -> daire
            parts = self.subtype_path.strip('/').split('/')
            if len(parts) >= 2:
                return parts[-1].replace('-', '_')
        return None
    
    def get_file_prefix(self) -> str:
        """Alt kategori varsa dosya öneki oluştur"""
        if self.subtype_name:
            return f"hepsiemlak_{self.listing_type}_{self.category}_{self.subtype_name}"
        return f"hepsiemlak_{self.listing_type}_{self.category}"

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
            f"📍 Taranıyor: {location_name}",
            f"🌐 {location_url}",
            "🧭 Yöntem: selenium",
        )

    def _log_location_plan(self, location_name: str, pages_to_scrape: int) -> None:
        task_log.line(f"{location_name}: scraping {pages_to_scrape} pages via selenium")
        task_log.line(f"📄 {pages_to_scrape} sayfa taranacak")

    def _log_page_start(self, location_name: str, page_num: int, total_pages: int) -> None:
        task_log.line(f"🔍 [{page_num}/{total_pages}] {location_name} - Sayfa {page_num} taranıyor...")

    def _log_page_result(self, page_num: int, extracted_count: int, new_count: int, updated_count: int, unchanged_count: int) -> None:
        task_log.line(f"   ✅ Sayfa {page_num}: {extracted_count} ilan çıkarıldı")
        task_log.line(f"   💾 Sayfa {page_num}: {new_count} yeni, {updated_count} güncellendi, {unchanged_count} değişmedi")

    def _log_location_complete(self, location_name: str, listing_count: int) -> None:
        task_log.line(f"✅ {location_name} tamamlandı - {listing_count} ilan işlendi")

    def _log_retry_round(self, retry_round: int, max_retries: int, failed_count: int) -> None:
        task_log.section(
            f"🔄 YENİDEN DENEME #{retry_round}/{max_retries}",
            f"📊 {failed_count} başarısız sayfa tekrar taranacak",
        )

    def _log_retry_summary(self, successful_retries: int, failed_count: int) -> None:
        task_log.section(
            "📊 RETRY ÖZETİ",
            f"   ✅ Başarılı retry: {successful_retries}",
            f"   ❌ Kalan başarısız: {failed_count}",
        )

    def _log_final_summary(self, stopped_early: bool, city_count: int, total_listings: int) -> None:
        if stopped_early:
            task_log.section(
                "⚠️ ERKEN DURDURULDU",
                f"Taranan Şehir Sayısı: {city_count}",
                f"Toplam İlan Sayısı: {total_listings}",
                level="warning",
            )
        elif total_listings > 0:
            task_log.section(
                "TARAMA BAŞARIYLA TAMAMLANDI",
                f"Taranan Şehir Sayısı: {city_count}",
                f"Toplam İlan Sayısı: {total_listings}",
            )
        else:
            task_log.section("HIC ILAN BULUNAMADI", level="warning")
    
    def extract_listing_data(self, container) -> Optional[Dict[str, Any]]:
        """Kategori parser'ı ile ilan verisini çıkar"""
        return self.parser.extract_listing_data(container)
    
    def parse_category_details(self, quick_info: str, title: str) -> Dict[str, Any]:
        """HepsiEmlak için kullanılmaz - parse işlemi extract_category_data ile yapılır"""
        return {}
    
    def get_cities(self) -> List[str]:
        """Tüm şehirleri al ve kullanıcının seçmesini sağla"""
        print(f"\n{self.category.capitalize()} sitesine gidiliyor...")
        self.driver.get(self.base_url)
        time.sleep(5)  # HepsiEmlak için sabit 5 saniye - sayfa tam yüklensin
        
        try:
            # Şehir dropdown'ını bul
            city_dropdown_sel = self.common_selectors.get("city_dropdown")
            city_dropdown = self.wait_for_clickable(city_dropdown_sel)
            
            if not city_dropdown:
                logger.error("Şehir dropdown'ı bulunamadı")
                return []
            
            # JS click ile menüyü aç (Selenium'un objeye tıklayamama riskine karşı)
            self.driver.execute_script("arguments[0].click();", city_dropdown)
            print("Şehir dropdown'ı açıldı...")
            time.sleep(3)  # Dropdown açılması için 3 saniye
            
            # Dropdown'ı genişlet
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
                logger.error("Tıklama sonrası şehir listesi görüntülenemedi")
                return []
            
            # Şehir öğelerini al
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
            
            # Şehirleri 4 sütunda göster
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
            
            # Dropdown'ı kapat
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
        """API için şehir listesi al (etkileşimsiz)"""
        return self.get_cities()
    
    def select_cities(self, cities: List[str]) -> List[str]:
        """Kullanıcının birden fazla şehir seçmesini sağla"""
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
                
                # İndeksleri korumak için ters sırada sil
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
        """API için şehir seç"""
        if not target_cities:
            return []
        
        selected = []
        for city in target_cities:
            # Doğrudan eşleştirme
            if city in all_cities:
                selected.append(city)
                continue
                
            # Büyük/küçük harf duyarsız eşleştirme
            found = False
            for ac in all_cities:
                if ac.lower() == city.lower():
                    selected.append(ac)
                    found = True
                    break
            if not found:
                 logger.warning(f"Şehir bulunamadı: {city}")
        
        return selected
    
    def select_single_city(self, city_name: str) -> bool:
        """Tek bir şehir seç - doğrudan şehir URL'ine git"""
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
            
            # HepsiEmlak URL formatı: ayas-kiralik/mustakil-ev (şehir-tip/subtype)
            # Subtype path varsa: şehir-tip/subtype
            # Subtype yoksa: şehir-tip (konut ana kategori) veya şehir-tip/arsa
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
                # Ana kategori için config'den path al
                category_path = self.hepsiemlak_config.categories.get(self.listing_type, {}).get(self.current_category, '')
                # /kiralik -> şehir-kiralik (konut)
                # /kiralik/arsa -> şehir-kiralik/arsa
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
            time.sleep(5)  # Sayfa tam yüklensin
            
            # URL doğru mu kontrol et
            current_url = self.driver.current_url
            if city_slug in current_url:
                return True
            else:
                task_log.line(f"⚠️ {city_name} sayfasına gidilemedi. URL: {current_url}", level="warning")
                return False
            
        except Exception as e:
            task_log.line(f"Error selecting city {city_name}: {e}", level="error")
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

    def _normalize_text(self, text: str) -> str:
        """URL için Türkçe karakterleri dönüştür ve slug oluştur"""
        import unicodedata
        text = unicodedata.normalize('NFC', text)
        replacements = {
            'İ': 'i', 'I': 'i', 'Ğ': 'g', 'Ü': 'u', 'Ş': 's', 'Ö': 'o', 'Ç': 'c',
            'ı': 'i', 'ğ': 'g', 'ü': 'u', 'ş': 's', 'ö': 'o', 'ç': 'c'
        }
        for tr, en in replacements.items():
            text = text.replace(tr, en)
        return text.lower().replace(' ', '-')

    def get_district_urls_from_dropdown(self, city_name: str) -> Dict[str, str]:
        """Şehir sayfasındaki ilçe dropdown'ından gerçek URL'leri çek ve {ilçe_adı: url} sözlüğü döndür"""
        district_urls = {}
        
        try:
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            
            # Önce şehir sayfasına git
            city_slug = self._normalize_text(city_name)
            
            # HepsiEmlak URL formatı: sehir-kiralik/subtype
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
            
            # İlçe dropdown'ını bul ve tıkla
            try:
                # "İlçe Seçiniz" placeholder'ı olan dropdown container'ını bul
                dropdown = None
                try:
                    # Placeholder span'ını bul ve üst konteyner'a tıkla
                    placeholder = self.driver.find_element(
                        By.XPATH, "//span[contains(@class, 'he-select-base__placeholder') and contains(text(), 'İlçe')]"
                    )
                    dropdown = placeholder.find_element(By.XPATH, "..")  # Üst eleman
                except:
                    # Alternatif: doğrudan container'ı bul
                    containers = self.driver.find_elements(By.CSS_SELECTOR, "div.he-select-base__container")
                    for cont in containers:
                        if "İlçe" in cont.text:
                            dropdown = cont
                            break

                if not dropdown:
                    task_log.line("⚠️ İlçe dropdown'ı bulunamadı", level="warning")
                    return district_urls

                # Dropdown'ı aç
                self.driver.execute_script("arguments[0].click();", dropdown)
                time.sleep(2)  # Liste yüklensin

                # JavaScript ile tüm ilçeleri bir seferde al (scroll gerektirmez)
                try:
                    # Tüm linkleri JS ile çek - görünürlük önemli değil
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

                    task_log.line(f"   📜 {len(district_urls)} ilçe JS ile toplandı")

                except Exception as js_error:
                    task_log.line(f"JS ile ilçe alma hatası: {js_error}", level="warning")

                # Dropdown'ı kapat
                try:
                    self.driver.find_element(By.TAG_NAME, "body").click()
                except:
                    pass

                task_log.line(f"📊 {len(district_urls)} ilçe URL'i bulundu")

            except Exception as e:
                task_log.line(f"Dropdown'dan URL çekme hatası: {e}", level="warning")
            
            return district_urls
            
        except Exception as e:
            task_log.line(f"get_district_urls_from_dropdown hatası: {e}", level="error")
            return district_urls

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

            # HepsiEmlak URL formatı: ilce-kiralik/subtype (ilce-tip/subtype)
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
            time.sleep(5)  # Sayfa tam yüklensin

            # URL doğru mu kontrol et
            current_url = self.driver.current_url
            if district_slug in current_url:
                return True
            else:
                task_log.line(f"⚠️ {district_name} sayfasına gidilemedi. URL: {current_url}", level="warning")
                return False

        except Exception as e:
            task_log.line(f"Error selecting district {district_name}: {e}", level="error")
            return False

    def search_listings(self) -> bool:
        """Arama butonuna tıkla ve sonuçları bekle"""
        try:
            search_selectors = self.common_selectors.get("search_buttons", [])
            
            for selector in search_selectors:
                try:
                    search_button = self.wait_for_clickable(selector, timeout=5)
                    if search_button:
                        self.driver.execute_script("arguments[0].click();", search_button)
                        print("Arama yapılıyor...")
                        self.random_long_wait()  # Gizli mod: arama sonrası
                        
                        # Sonuçları bekle
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
        """Sayfalamadan toplam sayfa sayısını al"""
        try:
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            
            # Önce toplam ilan sayısını kontrol et - 24 veya daha az ise pagination olmaz
            try:
                listing_count_element = self.driver.find_element(
                    By.CSS_SELECTOR, "span.applied-filters__count"
                )
                count_text = listing_count_element.text.strip()
                # "için 2.972 ilan bulundu" -> 2972
                # Türkçe binlik ayırıcı noktayı kaldır
                import re
                # Önce noktaları kaldır (binlik ayırıcı), sonra sayıyı bul
                count_text_clean = count_text.replace('.', '')
                match = re.search(r'(\d+)', count_text_clean)
                if match:
                    total_listings = int(match.group(1))
                    if total_listings <= 24:
                        print(f"📊 Toplam {total_listings} ilan - tek sayfa (pagination yok)")
                        return 1
                    else:
                        print(f"📊 Toplam {total_listings} ilan tespit edildi")
            except Exception:
                pass  # İlan sayısı bulunamazsa pagination kontrolüne geç
            
            # Sayfalama kontrolü - ul.he-pagination__links içindeki a elementleri
            max_retries = 5
            page_links = []

            for retry in range(max_retries):
                try:
                    wait = WebDriverWait(self.driver, 10)
                    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "ul.he-pagination__links")))
                    page_links = self.driver.find_elements(By.CSS_SELECTOR, "ul.he-pagination__links a")
                    if page_links:
                        print(f"✓ Pagination bulundu: {len(page_links)} link")
                        break
                except Exception:
                    pass

                if retry < max_retries - 1:
                    print(f"⚠️ Pagination bulunamadı, tekrar deneniyor... ({retry + 1}/{max_retries})")
                    time.sleep(3)
                else:
                    print(f"⚠️ Pagination bulunamadı - tek sayfa varsayılıyor")

            # Sayfa sayısını bul - en büyük sayıyı al
            max_page = 1
            for link in page_links:
                text = link.text.strip()

                # Sadece rakam olan linkleri kontrol et (1, 2, 3, ..., 421 gibi)
                # "..." gibi break-view'ları atla
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
        """Tek bir şehir için tüm ilanları tara"""
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
            progress_callback(f"{city} için tarama başlatılıyor...", current=0, total=100)

        try:
            # Şehir seç (doğrudan şehir URL'ine gider)
            if not self.select_single_city(city):
                task_log.line(f"❌ {city} seçilemedi, atlanıyor", level="error")
                return []

            # Sıfır sonuç kontrolü
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
                            task_log.line(f"⚠️ {city} için ilan bulunamadı", level="warning")
                            return []
            except Exception:
                pass

            # Toplam sayfa sayısını al
            total_pages = self.get_total_pages()

            # Sayfa sayısını al (None = limit yok, tüm sayfalar)
            if api_mode:
                 if max_pages is not None:
                     pages_to_scrape = min(max_pages, total_pages)
                 else:
                     pages_to_scrape = total_pages
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

            self._log_location_plan(city, pages_to_scrape)

            city_listings = []
            total_new_listings = 0  # Sadece yeni eklenen ilan sayısı

            # Sayfaları tara
            for page in range(1, pages_to_scrape + 1):
                # Durdurma kontrolü - her sayfa başında kontrol et
                if is_stop_requested():
                    task_log.line(f"⚠️ Durdurma isteği alındı! {total_new_listings} yeni ilan kaydediliyor...", level="warning")
                    break

                self._log_page_start(city, page, pages_to_scrape)

                if progress_callback:
                    # İlerleme: tamamlanan sayfa sayısı üzerinden hesapla
                    # Sayfa 5 taranmaya başladığında 4 tamamlanmış = %80
                    completed_pages = page - 1
                    page_progress = int((completed_pages / pages_to_scrape) * 100)
                    progress_callback(f"{city} - Sayfa {page}/{pages_to_scrape} taranıyor...", current=page, total=pages_to_scrape, progress=page_progress)

                page_url = self.driver.current_url.split('?')[0]
                if page > 1:
                    # Şehir URL'ini kullan (base_url değil!)
                    page_url = f"{page_url}?page={page}"
                    self.driver.get(page_url)
                    self.random_long_wait()  # Gizli mod: sayfa geçişi
                    
                # Sonuçları bekle - timeout hatalarını takip et
                result_element = self.wait_for_element(self.common_selectors.get("listing_results"))
                
                if result_element is None:
                    # Zaman aşımı - sayfa yüklenemedi, başarısız sayfa olarak kaydet
                    task_log.line(f"   ⚠️ Sayfa {page} yüklenemedi - retry listesine eklendi", level="warning")
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

                # 0 ilan bulunduysa ve bu beklenmiyorsa başarısız sayfa olarak işaretle
                if len(page_listings) == 0 and page > 1:
                    task_log.line(f"   ⚠️ Sayfa {page}'de 0 ilan - retry listesine eklendi", level="warning")
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

                    # Her sayfa sonrası DB'ye anında kaydet
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
                    self.random_medium_wait()  # Gizli mod: sayfalar arası

            self._log_location_complete(city, len(city_listings))
            return city_listings

        except Exception as e:
            task_log.line(f"❌ {city} tarama hatası: {e}", level="error")
            return []

    def scrape_city_with_districts(self, city: str, districts: List[str], max_pages: int = None, progress_callback=None, stop_checker=None) -> Dict[str, List[Dict[str, Any]]]:
        """Bir şehir için belirtilen ilçeleri ayrı ayrı tara ve kaydet"""
        all_results = {}  # İlçe -> İlanlar mapping
        total_new_listings = 0  # Sadece yeni eklenen ilan sayısı

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
            f"📍 Taranıyor: {city}",
            "🎯 İlçe filtreli tarama",
            "🧭 Yöntem: selenium",
        )

        # İlçe seçimi yoksa tüm şehri scrape et
        if not districts or len(districts) == 0:
            task_log.line(f"{city}: tüm ilçeler taranıyor")
            # Şehir bazlı kayıt için eski formatta döndür
            city_listings = self.scrape_city(city, max_pages, api_mode=True, progress_callback=progress_callback, stop_checker=_stop_checker)
            return {city: city_listings}

        task_log.line(f"📋 Seçili ilçeler: {', '.join(districts)}")
        task_log.line(f"🎯 {city} - {len(districts)} ilçe ayrı ayrı taranacak")

        # Önce dropdown'dan gerçek URL'leri al
        task_log.line(f"🔍 {city} için ilçe URL'leri alınıyor...")
        district_url_map = self.get_district_urls_from_dropdown(city)

        if not district_url_map:
            task_log.line(f"⚠️ {city} için ilçe URL'leri alınamadı, manuel URL oluşturulacak", level="warning")

        # Her ilçeyi ayrı ayrı tara
        for idx, district in enumerate(districts, 1):
            # Durdurma kontrolü - her ilçe başında kontrol et
            if is_stop_requested():
                task_log.line(f"⚠️ Durdurma isteği alındı! {len(all_results)} ilçe kaydedildi.", level="warning")
                break

            district_listings = []  # Bu ilçenin ilanları

            try:
                # Gerçek URL varsa onu kullan, yoksa manuel oluştur
                real_url = district_url_map.get(district)
                location_url = real_url or self._build_location_url(district)
                if location_url.startswith('/'):
                    location_url = f"https://www.hepsiemlak.com{location_url}"
                self._log_location_start(f"{city} / {district}", location_url)

                if real_url:
                    # Göreceli URL'yi tam URL'ye çevir
                    if real_url.startswith('/'):
                        real_url = f"https://www.hepsiemlak.com{real_url}"
                    self.driver.get(real_url)
                    time.sleep(5)

                    # URL doğru mu kontrol et
                    if district.lower().replace(' ', '-') in self.driver.current_url.lower() or \
                       self._normalize_text(district) in self.driver.current_url.lower():
                        pass
                    else:
                        task_log.line(f"⚠️ {district} - URL redirect olmuş olabilir: {self.driver.current_url}", level="warning")
                else:
                    # Yedek: Manuel URL oluştur
                    if not self.select_single_district(district):
                        task_log.line(f"⚠️ {district} ilçesi yüklenemedi, atlanıyor", level="warning")
                        continue

                # Sıfır sonuç kontrolü - daha güvenilir kontrol
                try:
                    # Önce gerçek ilan sayısını kontrol et
                    listing_count_elem = self.driver.find_elements(
                        By.CSS_SELECTOR, "span.applied-filters__count"
                    )
                    if listing_count_elem:
                        count_text = listing_count_elem[0].text.strip()
                        # "için 0 ilan" veya "0 ilan bulundu" kontrolü
                        count_text_clean = count_text.replace('.', '')
                        import re
                        match = re.search(r'(\d+)', count_text_clean)
                        if match:
                            actual_count = int(match.group(1))
                            if actual_count == 0:
                                task_log.line(f"⚠️ {district} için ilan bulunamadı", level="warning")
                                continue
                except Exception as e:
                    logger.debug(f"İlan sayısı kontrolü hatası: {e}")

                # Toplam sayfa sayısını al
                total_pages = self.get_total_pages()

                pages_to_scrape = min(max_pages, total_pages) if max_pages is not None else total_pages
                self._log_location_plan(f"{city} / {district}", pages_to_scrape)

                # Bu ilçe için sayfaları tara
                for page in range(1, pages_to_scrape + 1):
                    # Durdurma kontrolü - her sayfa başında kontrol et
                    if is_stop_requested():
                        task_log.line(f"⚠️ Durdurma isteği alındı! {district} için {len(district_listings)} ilan kaydediliyor...", level="warning")
                        # Mevcut ilçe verilerini kaydet
                        if district_listings:
                            all_results[district] = district_listings
                            self._save_district_data(city, district, district_listings)
                        break

                    self._log_page_start(f"{city} / {district}", page, pages_to_scrape)

                    if progress_callback:
                        # İlerleme: ilçe ve sayfa bilgisini birlikte göster
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
                    
                    # Sonuçları bekle - timeout hatalarını takip et
                    result_element = self.wait_for_element(self.common_selectors.get("listing_results"))
                    
                    if result_element is None:
                        # Zaman aşımı - sayfa yüklenemedi, başarısız sayfa olarak kaydet
                        task_log.line(f"   ⚠️ Sayfa {page} yüklenemedi - retry listesine eklendi", level="warning")
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

                    # 0 ilan bulunduysa ve bu beklenmiyorsa başarısız sayfa olarak işaretle
                    if len(page_listings) == 0 and page > 1:
                        task_log.line(f"   ⚠️ Sayfa {page}'de 0 ilan - retry listesine eklendi", level="warning")
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

                        # Her sayfa sonrası DB'ye anında kaydet
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

                # İlçe verilerini kaydet
                if district_listings:
                    all_results[district] = district_listings
                    self._log_location_complete(f"{city} / {district}", len(district_listings))

                    # Her ilçeyi hemen kaydet (bellek tasarrufu ve güvenlik için)
                    self._save_district_data(city, district, district_listings)
                else:
                    task_log.line(f"⚠️ {district} - İlan bulunamadı", level="warning")

                # İlçeler arası bekleme
                if idx < len(districts):
                    self.random_medium_wait()

            except Exception as e:
                task_log.line(f"❌ {district} tarama hatası: {e}", level="error")
                continue

        total_listings = sum(len(listings) for listings in all_results.values())
        task_log.section(
            f"✅ {city} - TÜM İLÇELER TAMAMLANDI",
            f"Toplam İlan Sayısı: {total_listings}",
            f"Taranan İlçe Sayısı: {len(all_results)}",
        )
        return all_results

    def _save_district_data(self, city: str, district: str, listings: List[Dict[str, Any]]):
        """İlçe istatistiklerini güncelle (DB kaydetme sayfa bazlı yapılıyor)"""
        if not listings:
            return
        # Not: Bu fonksiyon artık kullanılmıyor, yeni ilan sayısı callback içinde hesaplanıyor
        task_log.line(f"✅ {city}/{district} - {len(listings)} ilan işlendi")

    def scrape_current_page(self, fallback_city: str = None, fallback_district: str = None) -> List[Dict[str, Any]]:
        """Mevcut sayfadaki tüm ilanları tara; lokasyon bulunamazsa fallback_city ve fallback_district kullanılır"""
        listings = []

        try:
            container_sel = self.common_selectors.get("listing_container")
            self.wait_for_element(self.common_selectors.get("listing_results"))

            elements = self.driver.find_elements(By.CSS_SELECTOR, container_sel)

            for element in elements:
                try:
                    data = self.parser.extract_listing_data(element)
                    if data:
                        # Yedek: Lokasyon parse edilemezse, taranan şehir/ilçeyi kullan
                        if fallback_city and (not data.get('il') or data.get('il') == 'Belirtilmemiş'):
                            data['il'] = fallback_city
                        if fallback_district and (not data.get('ilce') or data.get('ilce') == 'Belirtilmemiş'):
                            data['ilce'] = fallback_district
                        listings.append(data)
                    time.sleep(random.uniform(0.02, 0.08))  # Gizli mod
                except Exception as e:
                    continue

        except Exception as e:
            task_log.line(f"❌ Sayfa tarama hatası: {e}", level="error")

        return listings
    
    def start_scraping_api(self, max_pages: int = 1, progress_callback=None, stop_checker=None):
        """API tarama giriş noktası; max_pages, progress_callback ve stop_checker parametreleri alır"""
        task_log.line(f"API: HepsiEmlak {self.listing_type.capitalize()} {self.category.capitalize()} Scraper (selenium)")

        # Durdurma denetleyicisini iç metotlarda kullanmak için sakla
        self._stop_checker = stop_checker

        def is_stop_requested():
            """Durdurma isteğini kontrol et - hem Celery hem bellek içi destekler"""
            if stop_checker and stop_checker():
                return True
            # Celery dışı çağrılar için bellek içi duruma geri dön
            try:
                from api.status import task_status
                return task_status.is_stop_requested()
            except:
                return False

        try:
            if not self.selected_cities:
                 task_log.line("No cities provided for API scrape", level="error")
                 return

            # Her şehri tara
            all_results = {}
            total_listings_count = 0
            total_cities = len(self.selected_cities)

            stopped_early = False  # Erken durdurulup durdurulmadığını takip et

            for city_idx, city in enumerate(self.selected_cities, 1):
                # Durdurma kontrolü - kullanıcı durdur dediyse mevcut verileri kaydet
                if is_stop_requested():
                    task_log.line(f"⚠️ Durdurma isteği alındı! {len(all_results)} şehir tarandı.", level="warning")
                    stopped_early = True
                    break

                # Toplam ilerleme hesabı için sarmalayıcı callback
                # city_idx ve total_cities'i closure'a alıyoruz
                # progress_callback varsa (Celery) onu kullan, yoksa task_status'u dene
                def make_city_progress_callback(current_city_idx, num_cities, city_name):
                    def city_progress_callback(msg, current=None, total=None, progress=None):
                        # Şehir içi progress'i toplam progress'e çevir
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
                            # Bellek içi task_status'a geri dön
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

                # İlçe filtreleme var mı kontrol et
                if self.selected_districts and city in self.selected_districts:
                    districts = self.selected_districts[city]
                    task_log.line(f"🎯 {city} için ilçe filtresi aktif: {len(districts)} ilçe")
                    task_log.line(f"📍 İlçeler: {', '.join(districts)}")

                    # scrape_city_with_districts artık Dict[district -> listings] döndürüyor
                    # VE her ilçeyi otomatik olarak kaydediyor
                    district_results = self.scrape_city_with_districts(
                        city,
                        districts=districts,
                        max_pages=max_pages,
                        progress_callback=city_callback
                    )

                    # Sadece istatistik için tutuyoruz (zaten kaydedildi)
                    if district_results:
                        all_results[city] = district_results
                        total_listings_count += sum(len(listings) for listings in district_results.values())
                else:
                    # İlçe seçimi yoksa tüm şehri tara ve kaydet
                    task_log.line(f"📍 {city} - Tüm ilçeler taranacak (filtre yok)")
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
                        # DB kaydetme scrape_city içinde sayfa bazlı yapılıyor

                self.random_medium_wait()  # Gizli mod: şehirler arası

            # Özet bilgi (veriler zaten kaydedildi)
            if all_results:
                total = total_listings_count
                self._log_final_summary(stopped_early, len(all_results), total)
            else:
                self._log_final_summary(stopped_early, 0, 0)

            # ============================================================
            # RETRY MEKANİZMASI - Başarısız sayfaları yeniden dene
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

                # İlerleme callback ile durumu güncelle
                if progress_callback:
                    progress_callback(
                        f"🔄 Retry #{retry_round} - {len(failed_pages)} sayfa",
                        current=0,
                        total=len(failed_pages),
                        progress=0
                    )

                # Her başarısız sayfa için yeni tarayıcı ile dene
                for idx, page_info in enumerate(failed_pages, 1):
                    # Durdurma kontrolü
                    if is_stop_requested():
                        task_log.line("⚠️ Retry durduruldu!", level="warning")
                        break

                    task_log.line(f"🔄 [{idx}/{len(failed_pages)}] {page_info.city}/{page_info.district or 'tüm'} - Sayfa {page_info.page_number}")

                    if progress_callback:
                        progress_callback(
                            f"🔄 Retry #{retry_round}: {page_info.city} Sayfa {page_info.page_number}",
                            current=idx,
                            total=len(failed_pages),
                            progress=int((idx / len(failed_pages)) * 100)
                        )
                    
                    try:
                        # Yeni tarayıcı oturumu aç
                        retry_manager = DriverManager()
                        retry_driver = retry_manager.start()
                        
                        try:
                            # Doğrudan URL'e git
                            task_log.line(f"   🌐 {page_info.url}")
                            retry_driver.get(page_info.url)
                            time.sleep(5)  # Sayfa yüklensin
                            
                            # Sonuçları bekle
                            from selenium.webdriver.support.ui import WebDriverWait
                            from selenium.webdriver.support import expected_conditions as EC
                            
                            wait = WebDriverWait(retry_driver, 30)
                            try:
                                wait.until(EC.presence_of_element_located(
                                    (By.CSS_SELECTOR, self.common_selectors.get("listing_results"))
                                ))
                                
                                # İlanları tara
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
                                        task_log.line(f"   ✅ {len(listings)} ilan bulundu!")
                                        
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
                                        
                                        # Başarılı olarak işaretle
                                        failed_pages_tracker.mark_as_success(
                                            page_info.city,
                                            page_info.district,
                                            page_info.page_number
                                        )
                                        successful_retries += 1
                                    else:
                                        task_log.line("   ⚠️ 0 ilan - devam ediliyor", level="warning")
                                        failed_pages_tracker.increment_retry_count(
                                            page_info.city, 
                                            page_info.district, 
                                            page_info.page_number
                                        )
                                else:
                                    task_log.line("   ⚠️ Element bulunamadı", level="warning")
                                    failed_pages_tracker.increment_retry_count(
                                        page_info.city, 
                                        page_info.district, 
                                        page_info.page_number
                                    )
                                    
                            except Exception as timeout_e:
                                task_log.line(f"   ❌ Timeout: {timeout_e}", level="warning")
                                failed_pages_tracker.increment_retry_count(
                                    page_info.city, 
                                    page_info.district, 
                                    page_info.page_number
                                )
                                
                        finally:
                            # Tarayıcıyı kapat
                            retry_manager.stop()
                            
                    except Exception as e:
                        task_log.line(f"Retry hatası: {e}", level="error")
                        failed_pages_tracker.increment_retry_count(
                            page_info.city, 
                            page_info.district, 
                            page_info.page_number
                        )
                    
                    # Sayfalar arası kısa bekleme
                    time.sleep(random.uniform(1, 2))

            # Son özet
            summary = failed_pages_tracker.get_summary()
            if summary["failed_count"] > 0 or successful_retries > 0:
                self._log_retry_summary(successful_retries, summary['failed_count'])
                
                if summary["failed_count"] > 0:
                    task_log.line(f"⚠️ {summary['failed_count']} sayfa retry sonrası hala başarısız", level="warning")
                    for fp in summary["failed_pages"]:
                        task_log.line(f"   - {fp['city']}/{fp['district'] or 'tüm'} Sayfa {fp['page_number']}: {fp['error']}", level="warning")

            return all_results

        except Exception as e:
            task_log.line(f"❌ API tarama hatası: {e}", level="error")
            raise e

