import time
import unicodedata
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

# TÜM SCRAPER MODÜLLERİNİ İMPORT ET
from konut_scraper import KonutScraper
from günlük_kiralik_konut_scraper import GunlukKiralikKonutScraper
from arsa_scraper import ArsaScraper
from isyeri_scraper import IsyeriScraper
from turistik_tesis_scraper import TuristikTesisScraper
from kat_karsiligi_arsa_scraper import KatKarsiligiArsaScraper
from devren_isyeri_scraper import DevrenIsyeriScraper

class EmlakJetCategorySelector:
    def __init__(self):
        self.driver = None
        self.setup_driver()
    
    def setup_driver(self):
        """Chrome driver'ı başlat"""
        chrome_options = Options()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
        chrome_options.add_experimental_option("useAutomationExtension", False)
        
        # Logları kapat
        chrome_options.add_argument("--log-level=3")
        chrome_options.add_argument("--disable-logging")
        chrome_options.add_argument("--disable-dev-tools")
        
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36"
        chrome_options.add_argument(f"user-agent={user_agent}")
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        self.wait = WebDriverWait(self.driver, 15)
    
    def get_main_categories(self):
        """Ana kategorileri (Satılık, Kiralık) ve alt kategorilerini alır"""
        try:
            print("🔄 EmlakJet ana sayfasına gidiliyor...")
            self.driver.get("https://www.emlakjet.com/")
            time.sleep(3)
            
            categories = {}
            
            # Satılık kategorisini al
            satilik_categories = self.get_category_submenu("Satılık")
            if satilik_categories:
                categories["Satılık"] = satilik_categories
            
            # Kiralık kategorisini al
            kiralik_categories = self.get_category_submenu("Kiralık")
            if kiralik_categories:
                categories["Kiralık"] = kiralik_categories
            
            return categories
            
        except Exception as e:
            print(f"Kategoriler alınırken hata: {e}")
            return {}
    
    def get_category_submenu(self, category_name):
        """Belirtilen ana kategoriye tıklar ve alt kategorileri alır"""
        try:
            # Ana kategori butonunu bul ve tıkla
            category_button = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, 
                    f"//div[@role='button' and contains(text(), '{category_name}')]"))
            )
            category_button.click()
            print(f"✓ {category_name} menüsü açıldı")
            time.sleep(1)
            
            # Alt kategorileri al
            sub_categories = []
            
            # Tüm açık menüleri bul
            sub_menus = self.driver.find_elements(By.CSS_SELECTOR, "ul.styles_wrapper__xd9_i")
            
            # Görünür olan menüyü bul
            visible_menu = None
            for menu in sub_menus:
                if menu.is_displayed():
                    visible_menu = menu
                    break
            
            if visible_menu:
                sub_items = visible_menu.find_elements(By.TAG_NAME, "a")
                for item in sub_items:
                    sub_name = item.text.strip()
                    sub_href = item.get_attribute("href")
                    if sub_name:
                        sub_categories.append({
                            'name': sub_name,
                            'url': sub_href
                        })
                        print(f"  └── {sub_name}")
            
            # Menüyü kapat
            self.driver.find_element(By.TAG_NAME, "body").click()
            time.sleep(1)
            
            return sub_categories
            
        except Exception as e:
            print(f"{category_name} alt kategorileri alınırken hata: {e}")
            return []
    
    def get_sub_sub_categories(self, current_url):
        """Mevcut sayfadaki alt kategorileri alır - BASİT YAKLAŞIM"""
        try:
            print(f"\n🔍 Alt kategoriler taranıyor...")
            
            # Sayfayı yenile
            self.driver.get(current_url)
            time.sleep(3)
            
            sub_sub_categories = []
            
            # Tüm alt kategori elementlerini bul
            category_elements = self.driver.find_elements(By.CSS_SELECTOR, "ul.styles_ulSubMenu__E0zyf li.styles_subMenu2__BskGl")
            
            for element in category_elements:
                try:
                    # Link elementini bul
                    link = element.find_element(By.TAG_NAME, "a")
                    
                    # Kategori ismini al (ilk span)
                    name_spans = link.find_elements(By.CSS_SELECTOR, "span")
                    if name_spans:
                        category_name = name_spans[0].text.strip()
                    else:
                        category_name = link.text.strip()
                    
                    # URL'yi al
                    category_url = link.get_attribute("href")
                    
                    # İlan sayısını al
                    ad_count = "0"
                    count_spans = link.find_elements(By.CSS_SELECTOR, "span.styles_adCount__M4_Qr")
                    if count_spans:
                        ad_count = count_spans[0].text.strip()
                    
                    if category_name and category_url:
                        # Ana kategorileri filtrele (Konut, Arsa vb.)
                        main_categories = ["Konut", "Arsa", "İşyeri", "Turistik Tesis", "Kat Karşılığı Arsa", "Devren İşyeri"]
                        if category_name not in main_categories:
                            sub_sub_categories.append({
                                'name': category_name,
                                'url': category_url,
                                'ad_count': ad_count
                            })
                            print(f"  └── {category_name} ({ad_count})")
                            
                except Exception as e:
                    continue
            
            return sub_sub_categories
            
        except Exception as e:
            print(f"Alt kategoriler alınırken hata: {e}")
            return []
    
    def display_menu(self, title, items, show_back=True, show_exit=True):
        """Menüyü güzel bir şekilde göster"""
        print(f"\n" + "="*50)
        print(f"🎯 {title}")
        print("="*50)

        for i, item in enumerate(items, 1):
            # Eğer item bir sözlükse (alt kategoriler)
            if isinstance(item, dict) and 'name' in item:
                # SADECE alt-alt kategorilerde ilan sayısı göster
                # Ana alt kategorilerde sadece isim göster
                if 'ad_count' in item and item['ad_count'] != "0" and "ALT KATEGORİLERİ" in title:
                    # Name'deki parantez içindeki sayıyı kaldır
                    clean_name = item['name'].split('(')[0].strip()
                    print(f"{i}. {clean_name} İlan Sayısı: {item['ad_count']}")
                else:
                    # Ana alt kategorilerde sadece isim
                    print(f"{i}. {item['name']}")
            # Eğer item string ise (ana kategoriler)
            else:
                print(f"{i}. {item}")

        option_number = len(items) + 1

        if show_back:
            print(f"{option_number}. ↩️ Üst menüye dön")
            option_number += 1

        if show_exit:
            print(f"{option_number}. 🚪 Çıkış")

        return option_number
    
    def get_user_choice(self, max_option):
        """Kullanıcıdan seçim al"""
        try:
            user_input = input(f"\nSeçiminiz (1-{max_option}): ").strip()
            
            # Çoklu seçim için özel kontrol - eğer virgül, boşluk veya tire içeriyorsa None döndür
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
    
    def normalize_category_name(self, category_name):
        """Kategori ismini scraper dosya ismi formatına normalize et"""
        # Küçük harfe çevir
        normalized = category_name.lower().strip()
        
        # Unicode karakterleri normalize et (ı -> i vb.)
        normalized = unicodedata.normalize('NFKD', normalized)
        normalized = normalized.encode('ascii', 'ignore').decode('ascii')
        
        # Boşlukları ve tireleri alt çizgi ile değiştir
        normalized = normalized.replace(' ', '_').replace('-', '_')
        
        # Türkçe karakterleri normalize et (ek güvenlik için)
        turkish_chars = {
            'ı': 'i', 'ş': 's', 'ü': 'u', 'ö': 'o', 
            'ğ': 'g', 'ç': 'c', 'İ': 'i', 'Ş': 's',
            'Ü': 'u', 'Ö': 'o', 'Ğ': 'g', 'Ç': 'c'
        }
        for turkish, english in turkish_chars.items():
            normalized = normalized.replace(turkish, english)
        
        # Çoklu alt çizgileri tek alt çizgiye çevir
        while '__' in normalized:
            normalized = normalized.replace('__', '_')
        
        # Başta ve sonda alt çizgi varsa temizle
        normalized = normalized.strip('_')
        
        return normalized
    
    def calculate_similarity(self, str1, str2):
        """İki string arasındaki benzerlik skorunu hesaplar (0-1 arası)"""
        # Kelime bazlı benzerlik
        words1 = set(str1.split('_'))
        words2 = set(str2.split('_'))
        
        # Ortak kelimeler
        common_words = words1.intersection(words2)
        all_words = words1.union(words2)
        
        if not all_words:
            return 0.0
        
        # Jaccard benzerliği (kelime bazlı)
        word_similarity = len(common_words) / len(all_words)
        
        # Karakter bazlı benzerlik (basit)
        longer = max(len(str1), len(str2))
        if longer == 0:
            return 0.0
        
        # Ortak karakterlerin oranı
        common_chars = set(str1) & set(str2)
        char_similarity = len(common_chars) / max(len(set(str1)), len(set(str2)), 1)
        
        # Kombinasyon: kelime benzerliği daha önemli
        similarity = (word_similarity * 0.7) + (char_similarity * 0.3)
        
        return similarity
    
    def start_appropriate_scraper(self, final_url, category_name, selected_path):
        """Kategoriye uygun scraper'ı başlat - En çok benzeyen scraper'ı seçer"""
        try:
            print(f"\n🚀 Scraper başlatılıyor: {selected_path}")
            
            # Kategori ismini normalize et (dosya ismi formatına)
            normalized = self.normalize_category_name(category_name)
            
            # Direkt dosya ismi → scraper sınıfı eşleştirmesi (Satılık ve Kiralık için aynı scraper'lar)
            scraper_map = {
                # Konut kategorileri
                'konut': KonutScraper,
                'gunluk_kiralik_konut': GunlukKiralikKonutScraper,
                'gunluk_kiralik': GunlukKiralikKonutScraper,
                
                # Arsa kategorileri
                'arsa': ArsaScraper,
                'kat_karsiligi_arsa': KatKarsiligiArsaScraper,
                'kat_karsiligi': KatKarsiligiArsaScraper,
                
                # İşyeri kategorileri
                'isyeri': IsyeriScraper,
                'is_yeri': IsyeriScraper,
                'devren_isyeri': DevrenIsyeriScraper,
                'devren_is_yeri': DevrenIsyeriScraper,
                'devren': DevrenIsyeriScraper,
                
                # Turistik Tesis
                'turistik_tesis': TuristikTesisScraper,
                'turistik': TuristikTesisScraper
            }
            
            # Önce tam eşleşme kontrolü
            scraper_class = scraper_map.get(normalized)
            
            if not scraper_class:
                # Tam eşleşme yoksa, benzerlik skoruna göre en yakın scraper'ı bul
                best_match = None
                best_score = 0.0
                best_key = None
                
                for map_key, map_scraper in scraper_map.items():
                    similarity = self.calculate_similarity(normalized, map_key)
                    if similarity > best_score:
                        best_score = similarity
                        best_match = map_scraper
                        best_key = map_key
                
                # Minimum benzerlik eşiği (0.3 = %30 benzerlik)
                if best_score >= 0.3:
                    scraper_class = best_match
                    print(f"ℹ️  Tam eşleşme bulunamadı, en benzer scraper seçildi: '{best_key}' (benzerlik: {best_score:.2%})")
                else:
                    # Çok düşük benzerlik, varsayılan scraper kullan
                    scraper_class = KonutScraper
                    print(f"ℹ️  '{category_name}' kategorisi için uygun scraper bulunamadı (max benzerlik: {best_score:.2%})")
                    print(f"   Normalize edilmiş isim: '{normalized}'")
                    print(f"   Varsayılan Konut Scraper kullanılıyor")
            
            if scraper_class:
                scraper = scraper_class(self.driver, final_url, None)
                print(f"✅ {scraper.__class__.__name__} başlatılıyor...")
                scraper.start_scraping()
            else:
                # Varsayılan olarak genel konut scraper'ı
                scraper = KonutScraper(self.driver, final_url, None)
                print(f"ℹ️  Varsayılan Konut Scraper kullanılıyor")
                scraper.start_scraping()
                
        except Exception as e:
            print(f"❌ Scraper başlatılırken hata: {e}")
    
    def main_menu(self):
        """Ana menüyü göster ve seçim al"""
        while True:
            print("🔄 Kategoriler taranıyor...")
            categories = self.get_main_categories()
            
            if not categories:
                print("❌ Kategori bulunamadı!")
                return
            
            # Ana kategorileri listele
            main_cats = list(categories.keys())
            max_option = self.display_menu("EMLAKJET KATEGORİLERİ", main_cats, show_back=False)
            
            choice = self.get_user_choice(max_option)
            if choice is None:
                continue
            
            if choice == max_option:  # Çıkış
                print("👋 Çıkış yapılıyor...")
                return
            
            if 1 <= choice <= len(main_cats):
                selected_main = main_cats[choice - 1]
                self.sub_category_menu(categories[selected_main], selected_main)
            else:
                print("❌ Geçersiz seçim!")
    
    def sub_category_menu(self, sub_categories, main_category_name):
        """Alt kategori menüsünü göster"""
        while True:
            max_option = self.display_menu(f"{main_category_name} ALT KATEGORİLERİ", sub_categories)
            
            choice = self.get_user_choice(max_option)
            if choice is None:
                continue
            
            if choice == max_option - 1:  # Üst menüye dön
                return
            elif choice == max_option:  # Çıkış
                print("👋 Çıkış yapılıyor...")
                exit()
            elif 1 <= choice <= len(sub_categories):
                selected_sub = sub_categories[choice - 1]
                print(f"\n✅ Seçilen: {main_category_name} → {selected_sub['name']}")
                self.final_category_menu(selected_sub['url'], selected_sub['name'])
            else:
                print("❌ Geçersiz seçim!")
    
    def final_category_menu(self, category_url, category_name):
        """Son kategori seçim menüsünü göster"""
        # Kategori sayfasına git
        if not self.go_to_selected_category(category_url):
            return
        
        # Alt kategorileri al
        sub_sub_categories = self.get_sub_sub_categories(category_url)
        
        while True:
            if sub_sub_categories:
                max_option = self.display_menu(f"{category_name.upper()} ALT KATEGORİLERİ", sub_sub_categories)
                
                choice = self.get_user_choice(max_option)
                if choice is None:
                    continue
                
                if choice == max_option - 1:  # Üst menüye dön
                    return
                elif choice == max_option:  # Çıkış
                    print("👋 Çıkış yapılıyor...")
                    exit()
                elif 1 <= choice <= len(sub_sub_categories):
                    selected_final = sub_sub_categories[choice - 1]
                    selected_path = f"{category_name} → {selected_final['name']}"
                    print(f"\n✅ Seçilen: {selected_path}")
                    
                    # Seçilen kategoriye git
                    final_url = selected_final['url']
                    self.go_to_selected_category(final_url)
                    
                    # Scraper'ı başlatma seçeneği
                    print("\n" + "="*50)
                    print("🎯 SCRAPER BAŞLATMA SEÇENEKLERİ")
                    print("="*50)
                    print("1. 🚀 Bu kategoride scraper başlat")
                    print("2. 🔄 Yeni kategori seç")
                    print("3. 🚪 Çıkış")
                    
                    final_choice = self.get_user_choice(3)
                    if final_choice == 1:
                        # Ana alt kategori ismini kullan (alt alt kategori değil)
                        self.start_appropriate_scraper(final_url, category_name, selected_path)
                        input("\n⏎ Devam etmek için Enter'a basın...")
                        return
                    elif final_choice == 2:
                        return  # Ana menüye dön
                    else:
                        print("👋 Çıkış yapılıyor...")
                        exit()
                else:
                    print("❌ Geçersiz seçim!")
            else:
                print(f"❌ '{category_name}' kategorisinde alt kategori bulunamadı!")
                
                # Direkt bu kategoride scraper başlatma seçeneği
                print("\n" + "="*50)
                print("🎯 SCRAPER BAŞLATMA SEÇENEKLERİ")
                print("="*50)
                print("1. 🚀 Bu kategoride scraper başlat")
                print("2. 🔄 Yeni kategori seç")
                print("3. 🚪 Çıkış")
                
                final_choice = self.get_user_choice(3)
                if final_choice == 1:
                    selected_path = f"{category_name}"
                    final_url = category_url
                    self.start_appropriate_scraper(final_url, category_name, selected_path)
                    input("\n⏎ Devam etmek için Enter'a basın...")
                    return
                elif final_choice == 2:
                    return  # Ana menüye dön
                else:
                    print("👋 Çıkış yapılıyor...")
                    exit()
    
    def go_to_selected_category(self, url):
        """Seçilen kategori sayfasına gider"""
        try:
            print(f"\n🌐 Sayfaya gidiliyor: {url}")
            self.driver.get(url)
            time.sleep(3)
            
            print(f"✅ Başarılı! Geçerli URL: {self.driver.current_url}")
            print(f"📄 Sayfa başlığı: {self.driver.title}")
            
            return True
            
        except Exception as e:
            print(f"❌ Sayfaya gidilirken hata: {e}")
            return False
    
    def close(self):
        """Driver'ı kapat"""
        if self.driver:
            self.driver.quit()


def main():
    """Ana fonksiyon"""
    selector = None
    try:
        selector = EmlakJetCategorySelector()
        selector.main_menu()
        
    except Exception as e:
        print(f"❌ Beklenmeyen hata: {e}")
    
    finally:
        if selector:
            selector.close()


if __name__ == "__main__":
    main()