import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

class EmlakJetCategorySelector:
    def __init__(self):
        self.driver = None
        self.selected_locations = {
            'iller': [],
            'ilceler': [], 
            'mahalleler': []
        }
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
    
    def get_location_options(self, location_type, current_url):
        """İl, ilçe veya mahalle seçeneklerini alır"""
        try:
            print(f"\n🔍 {location_type} seçenekleri taranıyor...")
            
            # Sayfayı yenile
            self.driver.get(current_url)
            time.sleep(3)
            
            location_options = []
            
            # Lokasyon linklerini bul
            location_links = self.driver.find_elements(By.CSS_SELECTOR, "p.styles_paragraph__QR1cn a.styles_link__7WOOd")
            
            for link in location_links:
                try:
                    location_name = link.text.strip()
                    location_url = link.get_attribute("href")
                    
                    if location_name and location_url:
                        location_options.append({
                            'name': location_name,
                            'url': location_url
                        })
                        print(f"  └── {location_name}")
                        
                except Exception as e:
                    continue
            
            return location_options
            
        except Exception as e:
            print(f"{location_type} seçenekleri alınırken hata: {e}")
            return []
    
    def display_selected_locations(self):
        """Seçilmiş lokasyonları göster"""
        if any(self.selected_locations.values()):
            print(f"\n📍 SEÇİLİ LOKASYONLAR:")
            if self.selected_locations['iller']:
                print(f"   🏙️  İller: {', '.join([il['name'] for il in self.selected_locations['iller']])}")
            if self.selected_locations['ilceler']:
                print(f"   🏘️  İlçeler: {', '.join([ilce['name'] for ilce in self.selected_locations['ilceler']])}")
            if self.selected_locations['mahalleler']:
                print(f"   🏡 Mahalleler: {', '.join([mah['name'] for mah in self.selected_locations['mahalleler']])}")
    
    def build_final_url(self, base_url):
        """Seçilen lokasyonlara göre final URL oluştur"""
        # Base URL'i kullan, çoklu seçim için özel URL yapısı gerekebilir
        # Bu basit versiyonda sadece base URL'i döndürüyoruz
        # İleride filtreleme parametreleri eklenebilir
        return base_url
    
    def location_selection_menu(self, current_url, selected_path):
        """İl, ilçe ve mahalle seçim menüsü - ÇOKLU SEÇİM"""
        base_url = current_url
        
        while True:
            print(f"\n🌍 LOKASYON SEÇİMİ - ÇOKLU SEÇİM")
            self.display_selected_locations()
            
            print(f"\n" + "="*50)
            print("🎯 LOKASYON SEÇİM MENÜSÜ")
            print("="*50)
            print("1. 🏙️  İl Ekle")
            print("2. 🏘️  İlçe Ekle") 
            print("3. 🏡 Mahalle Ekle")
            print("4. 🗑️  Seçilmiş Lokasyonları Temizle")
            print("5. ✅ Seçimleri Tamamla ve Devam Et")
            print("6. ↩️  Lokasyon Seçmeden Devam Et")
            print("7. 🚪 Çıkış")
            
            choice = self.get_user_choice(7)
            
            if choice == 1:
                self.add_province_selection(base_url, selected_path)
            elif choice == 2:
                if not self.selected_locations['iller']:
                    print("❌ Önce il seçmelisiniz!")
                    continue
                self.add_district_selection(base_url, selected_path)
            elif choice == 3:
                if not self.selected_locations['ilceler']:
                    print("❌ Önce ilçe seçmelisiniz!")
                    continue
                self.add_neighborhood_selection(base_url, selected_path)
            elif choice == 4:
                self.clear_selected_locations()
            elif choice == 5:
                if not any(self.selected_locations.values()):
                    print("❌ En az bir lokasyon seçmelisiniz!")
                    continue
                final_url = self.build_final_url(base_url)
                return final_url
            elif choice == 6:
                return base_url
            elif choice == 7:
                print("👋 Çıkış yapılıyor...")
                exit()
            else:
                print("❌ Geçersiz seçim!")
    
    def add_province_selection(self, base_url, selected_path):
        """İl ekleme menüsü"""
        print(f"\n🏙️  İL EKLEME")
        provinces = self.get_location_options("İller", base_url)
        if not provinces:
            print("❌ İl bulunamadı!")
            return
        
        while True:
            max_option = self.display_menu("LÜTFEN EKLENECEK İL SEÇİN (Çoklu seçim yapabilirsiniz)", provinces, show_back=True)
            print(f"{max_option-1}. ✅ Seçimleri Tamamla")
            
            choice = self.get_user_choice(max_option)
            
            if choice == max_option - 2:  # Üst menüye dön
                return
            elif choice == max_option - 1:  # Seçimleri tamamla
                if not self.selected_locations['iller']:
                    print("❌ En az bir il seçmelisiniz!")
                    continue
                return
            elif choice == max_option:  # Çıkış
                print("👋 Çıkış yapılıyor...")
                exit()
            elif 1 <= choice <= len(provinces):
                selected_province = provinces[choice - 1]
                
                # Aynı ili tekrar eklemeyi kontrol et
                if any(il['name'] == selected_province['name'] for il in self.selected_locations['iller']):
                    print(f"❌ {selected_province['name']} zaten seçilmiş!")
                    continue
                
                self.selected_locations['iller'].append(selected_province)
                print(f"✅ Eklendi: {selected_province['name']}")
            else:
                print("❌ Geçersiz seçim!")
    
    def add_district_selection(self, base_url, selected_path):
        """İlçe ekleme menüsü"""
        print(f"\n🏘️  İLÇE EKLEME")
        
        # Son seçilen ilin URL'sini kullan
        if self.selected_locations['iller']:
            last_province_url = self.selected_locations['iller'][-1]['url']
        else:
            print("❌ Önce il seçmelisiniz!")
            return
        
        districts = self.get_location_options("İlçeler", last_province_url)
        if not districts:
            print("❌ İlçe bulunamadı!")
            return
        
        while True:
            max_option = self.display_menu("LÜTFEN EKLENECEK İLÇE SEÇİN (Çoklu seçim yapabilirsiniz)", districts, show_back=True)
            print(f"{max_option-1}. ✅ Seçimleri Tamamla")
            
            choice = self.get_user_choice(max_option)
            
            if choice == max_option - 2:  # Üst menüye dön
                return
            elif choice == max_option - 1:  # Seçimleri tamamla
                return
            elif choice == max_option:  # Çıkış
                print("👋 Çıkış yapılıyor...")
                exit()
            elif 1 <= choice <= len(districts):
                selected_district = districts[choice - 1]
                
                # Aynı ilçeyi tekrar eklemeyi kontrol et
                if any(ilce['name'] == selected_district['name'] for ilce in self.selected_locations['ilceler']):
                    print(f"❌ {selected_district['name']} zaten seçilmiş!")
                    continue
                
                self.selected_locations['ilceler'].append(selected_district)
                print(f"✅ Eklendi: {selected_district['name']}")
            else:
                print("❌ Geçersiz seçim!")
    
    def add_neighborhood_selection(self, base_url, selected_path):
        """Mahalle ekleme menüsü"""
        print(f"\n🏡 MAHALLE EKLEME")
        
        # Son seçilen ilçenin URL'sini kullan
        if self.selected_locations['ilceler']:
            last_district_url = self.selected_locations['ilceler'][-1]['url']
        else:
            print("❌ Önce ilçe seçmelisiniz!")
            return
        
        neighborhoods = self.get_location_options("Mahalleler", last_district_url)
        if not neighborhoods:
            print("❌ Mahalle bulunamadı!")
            return
        
        while True:
            max_option = self.display_menu("LÜTFEN EKLENECEK MAHALLE SEÇİN (Çoklu seçim yapabilirsiniz)", neighborhoods, show_back=True)
            print(f"{max_option-1}. ✅ Seçimleri Tamamla")
            
            choice = self.get_user_choice(max_option)
            
            if choice == max_option - 2:  # Üst menüye dön
                return
            elif choice == max_option - 1:  # Seçimleri tamamla
                return
            elif choice == max_option:  # Çıkış
                print("👋 Çıkış yapılıyor...")
                exit()
            elif 1 <= choice <= len(neighborhoods):
                selected_neighborhood = neighborhoods[choice - 1]
                
                # Aynı mahalleyi tekrar eklemeyi kontrol et
                if any(mah['name'] == selected_neighborhood['name'] for mah in self.selected_locations['mahalleler']):
                    print(f"❌ {selected_neighborhood['name']} zaten seçilmiş!")
                    continue
                
                self.selected_locations['mahalleler'].append(selected_neighborhood)
                print(f"✅ Eklendi: {selected_neighborhood['name']}")
            else:
                print("❌ Geçersiz seçim!")
    
    def clear_selected_locations(self):
        """Seçilmiş lokasyonları temizle"""
        print(f"\n🗑️  LOKASYONLARI TEMİZLE")
        print("1. 🏙️  Sadece İlleri Temizle")
        print("2. 🏘️  Sadece İlçeleri Temizle") 
        print("3. 🏡 Sadece Mahalleleri Temizle")
        print("4. 💥 Tümünü Temizle")
        print("5. ↩️  İptal")
        
        choice = self.get_user_choice(5)
        
        if choice == 1:
            self.selected_locations['iller'].clear()
            print("✅ İller temizlendi!")
        elif choice == 2:
            self.selected_locations['ilceler'].clear()
            print("✅ İlçeler temizlendi!")
        elif choice == 3:
            self.selected_locations['mahalleler'].clear()
            print("✅ Mahalleler temizlendi!")
        elif choice == 4:
            self.selected_locations = {'iller': [], 'ilceler': [], 'mahalleler': []}
            print("✅ Tüm lokasyonlar temizlendi!")
        elif choice == 5:
            print("İptal edildi.")
        else:
            print("❌ Geçersiz seçim!")
    
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
            choice = int(input(f"\nSeçiminiz (1-{max_option}): "))
            return choice
        except ValueError:
            print("❌ Geçersiz giriş! Lütfen bir sayı girin.")
            return None
    
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
                    
                    # LOKASYON SEÇİMİ (İl, İlçe, Mahalle) - ÇOKLU SEÇİM
                    print(f"\n🌍 LOKASYON SEÇİMİ - ÇOKLU SEÇİM")
                    # Lokasyon seçiminden önce seçilmiş lokasyonları temizle
                    self.selected_locations = {'iller': [], 'ilceler': [], 'mahalleler': []}
                    final_url = self.location_selection_menu(final_url, selected_path)
                    
                    # Scraper'ı başlatma seçeneği
                    print("\n" + "="*50)
                    print("🎯 SCRAPER BAŞLATMA SEÇENEKLERİ")
                    print("="*50)
                    print("1. 🚀 Bu kategoride scraper başlat")
                    print("2. 🔄 Yeni kategori seç")
                    print("3. 🚪 Çıkış")
                    
                    final_choice = self.get_user_choice(3)
                    if final_choice == 1:
                        print(f"🚀 Scraper başlatılıyor: {final_url}")
                        print("📍 Seçilen Lokasyonlar:")
                        self.display_selected_locations()
                        # Burada ilgili scraper dosyasını import edip çalıştırabilirsiniz
                        # Örnek: 
                        # from kiralik_konut_scraper import KiralikKonutScraper
                        # scraper = KiralikKonutScraper(self.driver, final_url, self.selected_locations)
                        # scraper.start_scraping()
                        print("✅ Scraper başlatıldı! (Entegrasyon için hazır)")
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
                
                # İnceleme için bekle
                print(f"\n⏳ 30 saniye bekleniyor...")
                time.sleep(30)
                print("Bekleme süresi tamamlandı.")
                return
    
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