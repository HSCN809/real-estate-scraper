import time
import json
import csv
import os
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.options import Options

class TuristikTesisScraper:
    def __init__(self, driver, base_url, selected_locations=None):
        self.driver = driver
        self.base_url = base_url
        self.selected_locations = selected_locations or {}
        self.all_listings = []
        self.wait = WebDriverWait(self.driver, 10)
        
    def start_scraping(self):
        """Scraping işlemini başlat"""
        print(f"🚀 Turistik Tesis Scraper başlatılıyor: {self.base_url}")
        
        try:
            # Kullanıcıdan sayfa sayısını al
            max_pages = self.get_user_page_count()
            if max_pages is None:
                return
                
            # Sayfaları tara
            self.scrape_pages(max_pages)
            
            # Verileri kaydet
            self.save_data()
            
            print(f"\n✅ Scraping tamamlandı! Toplam {len(self.all_listings)} ilan bulundu.")
            
        except Exception as e:
            print(f"❌ Scraping sırasında hata: {e}")
    
    def get_user_page_count(self):
        """Kullanıcıdan kaç sayfa taranacağını al"""
        try:
            print(f"\n📄 Maksimum sayfa sayısını öğreniliyor...")
            max_available_pages = self.get_max_pages()
            print(f"📊 Sitede toplam {max_available_pages} sayfa bulunuyor.")
            
            while True:
                try:
                    user_input = input(f"\n🔢 Kaç sayfa taranacak? (1-{max_available_pages}): ").strip()
                    
                    if not user_input:
                        print("❌ Geçersiz giriş! Lütfen bir sayı girin.")
                        continue
                    
                    page_count = int(user_input)
                    
                    if page_count < 1:
                        print("❌ En az 1 sayfa seçmelisiniz!")
                        continue
                    
                    if page_count > max_available_pages:
                        print(f"❌ Maksimum {max_available_pages} sayfa seçebilirsiniz!")
                        continue
                    
                    print(f"✅ {page_count} sayfa taranacak...")
                    return page_count
                    
                except ValueError:
                    print("❌ Geçersiz giriş! Lütfen bir sayı girin.")
                except KeyboardInterrupt:
                    print("\n⏹️  İşlem kullanıcı tarafından iptal edildi.")
                    return None
                    
        except Exception as e:
            print(f"❌ Sayfa sayısı alınırken hata: {e}")
            return 1
    
    def scrape_pages(self, max_pages):
        """Belirtilen sayıda sayfayı tarar"""
        for current_page in range(1, max_pages + 1):
            print(f"\n🔍 Sayfa {current_page} taranıyor...")
            
            try:
                # Sayfaya git
                page_url = f"{self.base_url}?sayfa={current_page}" if current_page > 1 else self.base_url
                self.driver.get(page_url)
                time.sleep(2)
                
                # İlanları çek
                listings = self.scrape_current_page()
                self.all_listings.extend(listings)
                
                print(f"   ✅ Sayfa {current_page}: {len(listings)} ilan bulundu")
                
            except Exception as e:
                print(f"   ❌ Sayfa {current_page} taranırken hata: {e}")
                continue
    
    def get_max_pages(self):
        """Maksimum sayfa sayısını bul"""
        try:
            self.driver.get(self.base_url)
            time.sleep(2)
            
            # Sayfalama elementlerini bul
            pagination = self.driver.find_elements(By.CSS_SELECTOR, "ul.styles_list__zqOeW li")
            
            if not pagination:
                return 1
            
            # Sayfa numaralarını topla
            page_numbers = []
            for item in pagination:
                try:
                    # Aktif sayfa
                    active_page = item.find_element(By.CSS_SELECTOR, "span.styles_selected__hilA_")
                    page_numbers.append(int(active_page.text))
                except:
                    pass
                
                try:
                    # Link sayfaları
                    page_link = item.find_element(By.CSS_SELECTOR, "a")
                    page_text = page_link.text
                    if page_text.isdigit():
                        page_numbers.append(int(page_text))
                except:
                    pass
            
            return max(page_numbers) if page_numbers else 1
            
        except Exception as e:
            print(f"❌ Sayfa sayısı alınırken hata: {e}")
            return 1
    
    def scrape_current_page(self):
        """Mevcut sayfadaki ilanları çeker"""
        listings = []
        
        try:
            # İlan container'larını bul
            listing_containers = self.driver.find_elements(By.CSS_SELECTOR, "a.styles_wrapper__587DT")
            
            for container in listing_containers:
                try:
                    listing_data = self.extract_listing_data(container)
                    if listing_data:
                        listings.append(listing_data)
                        
                except Exception:
                    continue
            
        except Exception:
            pass
        
        return listings
    
    def extract_listing_data(self, container):
        """Tek bir ilanın verilerini çıkarır - TURİSTİK TESİS ÖZEL"""
        try:
            # HTML'DE GÖRDÜĞÜMÜZ TEMEL BİLGİLER
            title = self.get_element_text(container, "h3.styles_title__aKEGQ")
            location = self.get_element_text(container, "span.styles_location__OwJiQ")
            price = self.get_element_text(container, "span.styles_price__F3pMQ")
            
            # Quick info'dan temel detaylar
            quick_info = self.get_element_text(container, "div.styles_quickinfoWrapper__Vsnk5")
            
            # Görsel URL
            image_url = self.get_element_attribute(container, "img.styles_imageClass___SLvt", "src")
            
            # İlan URL
            listing_url = container.get_attribute("href")
            
            # Badge bilgileri
            badges = self.extract_badges(container)
            
            # Video ikonu kontrolü
            has_video = self.check_video_icon(container)
            
            # Turistik tesis özel detayları parse et
            details = self.parse_turistik_tesis_details(quick_info, title)
            
            listing_data = {
                'baslik': title,
                'lokasyon': location,
                'fiyat': price,
                'ilan_url': listing_url,
                'resim_url': image_url,
                'one_cikan': 'ÖNE ÇIKAN' in badges,
                'yeni': 'YENİ' in badges,
                'video_var': has_video,
                'tesis_tipi': details['tesis_tipi'],
                'metrekare': details['metrekare'],
                'yapim_yili': details['yapim_yili'],
                'isletme_tipi': details['isletme_tipi'],
                'tarih': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # Temel bilgiler eksikse atla
            if not all([title, location, price]):
                return None
                
            return listing_data
            
        except Exception:
            return None
    
    def parse_turistik_tesis_details(self, quick_info, title):
        """Turistik tesis özel detaylarını parse et"""
        details = {
            'tesis_tipi': '',
            'metrekare': '',
            'yapim_yili': '',
            'isletme_tipi': ''
        }
        
        # Quick info'dan tesis tipi ve metrekare
        if quick_info:
            try:
                # "Apart Otel | 1.800 m²" formatını parse et
                parts = [part.strip() for part in quick_info.split('|')]
                
                for part in parts:
                    if any(tip in part.lower() for tip in ['otel', 'apart', 'pansiyon', 'motel', 'tatil köyü', 'villa', 'butik']):
                        details['tesis_tipi'] = part
                    elif 'm²' in part or 'm2' in part.lower():
                        details['metrekare'] = part
            except:
                pass
        
        # Başlıktan yapım yılı ve işletme tipi çıkar
        if title:
            title_lower = title.lower()
            
            # Yapım yılı
            import re
            year_match = re.search(r'(\d{4})\s*yılı', title_lower)
            if year_match:
                details['yapim_yili'] = year_match.group(1)
            
            # İşletme tipi
            if 'hazır işletme' in title_lower or 'işletmeli' in title_lower:
                details['isletme_tipi'] = 'Hazır İşletme'
            elif 'devren' in title_lower:
                details['isletme_tipi'] = 'Devren'
            elif 'kiralamalı' in title_lower or 'kiralık' in title_lower:
                details['isletme_tipi'] = 'Kiralık'
        
        return details
    
    def check_video_icon(self, container):
        """Video ikonu olup olmadığını kontrol et"""
        try:
            video_icons = container.find_elements(By.CSS_SELECTOR, "div.styles_visitIcons__ZNI5l")
            return len(video_icons) > 0
        except:
            return False
    
    def extract_badges(self, container):
        """Badge bilgilerini çıkarır"""
        badges = []
        try:
            badge_elements = container.find_elements(By.CSS_SELECTOR, "div.styles_badgewrapper__pS0rt")
            for badge in badge_elements:
                badge_text = badge.text.strip()
                if badge_text:
                    badges.append(badge_text)
        except:
            pass
        return badges
    
    def get_element_text(self, container, selector):
        """Element metnini al"""
        try:
            element = container.find_element(By.CSS_SELECTOR, selector)
            return element.text.strip()
        except:
            return ""
    
    def get_element_attribute(self, container, selector, attribute):
        """Element attribute değerini al"""
        try:
            element = container.find_element(By.CSS_SELECTOR, selector)
            return element.get_attribute(attribute)
        except:
            return ""
    
    def save_data(self):
        """Verileri JSON ve CSV formatında kaydet"""
        if not self.all_listings:
            print("❌ Kaydedilecek veri bulunamadı!")
            return
        
        # Klasör oluştur
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        folder_name = f"scraped_turistik_tesis_data_{timestamp}"
        os.makedirs(folder_name, exist_ok=True)
        
        # JSON kaydet
        json_filename = os.path.join(folder_name, "turistik_tesis_ilanlari.json")
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(self.all_listings, f, ensure_ascii=False, indent=2)
        
        # CSV kaydet
        csv_filename = os.path.join(folder_name, "turistik_tesis_ilanlari.csv")
        self.save_to_csv(csv_filename)
        
        print(f"💾 Veriler kaydedildi:")
        print(f"   📄 JSON: {json_filename}")
        print(f"   📊 CSV: {csv_filename}")
    
    def save_to_csv(self, filename):
        """Verileri CSV formatında kaydet - TURİSTİK TESİS ÖZEL"""
        if not self.all_listings:
            return
        
        # Turistik tesis özel sütunlar
        fieldnames = [
            'baslik', 'lokasyon', 'fiyat', 'ilan_url', 'resim_url',
            'one_cikan', 'yeni', 'video_var', 'tesis_tipi', 'metrekare', 
            'yapim_yili', 'isletme_tipi', 'tarih'
        ]
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for listing in self.all_listings:
                writer.writerow(listing)

def setup_driver():
    """Chrome driver'ı sessiz modda başlat"""
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    
    # Tüm logları kapat
    chrome_options.add_argument("--log-level=3")
    chrome_options.add_argument("--disable-logging")
    chrome_options.add_argument("--disable-dev-tools")
    
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    chrome_options.add_argument(f"user-agent={user_agent}")
    
    driver = webdriver.Chrome(options=chrome_options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    return driver

# Test için standalone çalıştırma
def test_scraper():
    """Test fonksiyonu"""
    driver = setup_driver()
    
    try:
        # Test URL'si
        test_url = "https://www.emlakjet.com/satilik-turistik-tesis"
        
        scraper = TuristikTesisScraper(driver, test_url)
        scraper.start_scraping()
        
    except Exception as e:
        print(f"❌ Test sırasında hata: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    test_scraper()