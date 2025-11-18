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
    
    def display_menu(self, title, items, show_back=True, show_exit=True, selected_items=None):
        """Menüyü güzel bir şekilde göster"""
        print(f"\n" + "="*50)
        print(f"🎯 {title}")
        print("="*50)

        # Seçili item'ları kontrol etmek için set oluştur
        selected_items_set = set()
        if selected_items:
            for selected in selected_items:
                if isinstance(selected, dict) and 'name' in selected:
                    selected_items_set.add(selected['name'])
                elif isinstance(selected, str):
                    selected_items_set.add(selected)

        for i, item in enumerate(items, 1):
            # Seçili mi kontrol et
            is_selected = False
            if isinstance(item, dict) and 'name' in item:
                is_selected = item['name'] in selected_items_set
            elif isinstance(item, str):
                is_selected = item in selected_items_set
            
            checkmark = " ✅" if is_selected else ""
            
            # Eğer item bir sözlükse (alt kategoriler)
            if isinstance(item, dict) and 'name' in item:
                # SADECE alt-alt kategorilerde ilan sayısı göster
                # Ana alt kategorilerde sadece isim göster
                if 'ad_count' in item and item['ad_count'] != "0" and "ALT KATEGORİLERİ" in title:
                    # Name'deki parantez içindeki sayıyı kaldır
                    clean_name = item['name'].split('(')[0].strip()
                    print(f"{i}. {clean_name} İlan Sayısı: {item['ad_count']}{checkmark}")
                else:
                    # Ana alt kategorilerde sadece isim
                    print(f"{i}. {item['name']}{checkmark}")
            # Eğer item string ise (ana kategoriler)
            else:
                print(f"{i}. {item}{checkmark}")

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
    
    def display_selected_categories(self, selected_categories):
        """Seçili alt-alt kategorileri göster"""
        if selected_categories:
            print(f"\n📍 SEÇİLİ KATEGORİLER ({len(selected_categories)}):")
            for i, cat in enumerate(selected_categories, 1):
                print(f"   {i}. {cat['name']}")
        else:
            print(f"\n📍 SEÇİLİ KATEGORİLER: Henüz kategori seçilmedi")
    
    def multiple_category_selection_menu(self, sub_sub_categories):
        """Alt-alt kategoriler için çoklu seçim menüsü"""
        print(f"\n🎯 ÇOKLU KATEGORİ SEÇİMİ")
        print("Birden fazla kategori seçmek için numaraları virgülle veya boşlukla ayırarak girin.")
        print("Örnek: 1,3,5 veya 1 3 5 veya 1-5")
        
        while True:
            try:
                user_input = input(f"\nSeçimlerinizi girin (1-{len(sub_sub_categories)}): ").strip()
                
                if not user_input:
                    print("❌ Boş giriş! Lütfen numara girin.")
                    continue
                
                # Farklı formatları destekle
                selections = set()
                
                if ',' in user_input:
                    parts = user_input.split(',')
                    for part in parts:
                        part = part.strip()
                        if '-' in part:
                            range_parts = part.split('-')
                            if len(range_parts) == 2:
                                start = int(range_parts[0].strip())
                                end = int(range_parts[1].strip())
                                selections.update(range(start, end + 1))
                        else:
                            if part.isdigit():
                                selections.add(int(part))
                
                elif ' ' in user_input:
                    parts = user_input.split()
                    for part in parts:
                        part = part.strip()
                        if '-' in part:
                            range_parts = part.split('-')
                            if len(range_parts) == 2:
                                start = int(range_parts[0].strip())
                                end = int(range_parts[1].strip())
                                selections.update(range(start, end + 1))
                        else:
                            if part.isdigit():
                                selections.add(int(part))
                
                elif '-' in user_input:
                    range_parts = user_input.split('-')
                    if len(range_parts) == 2:
                        start = int(range_parts[0].strip())
                        end = int(range_parts[1].strip())
                        selections.update(range(start, end + 1))
                
                else:
                    if user_input.isdigit():
                        selections.add(int(user_input))
                
                # Seçimleri kontrol et
                valid_selections = []
                invalid_selections = []
                
                for selection in selections:
                    if 1 <= selection <= len(sub_sub_categories):
                        valid_selections.append(selection)
                    else:
                        invalid_selections.append(selection)
                
                if invalid_selections:
                    print(f"❌ Geçersiz numaralar: {invalid_selections}")
                
                if valid_selections:
                    selected_categories = []
                    for selection in valid_selections:
                        selected_item = sub_sub_categories[selection - 1]
                        selected_categories.append(selected_item)
                    
                    print(f"✅ {len(valid_selections)} kategori seçildi:")
                    for selection in valid_selections:
                        print(f"   - {sub_sub_categories[selection - 1]['name']}")
                    
                    return selected_categories
                else:
                    print("❌ Geçerli seçim yapılmadı!")
                    
            except ValueError:
                print("❌ Geçersiz giriş! Lütfen numara girin.")
            except Exception as e:
                print(f"❌ Hata: {e}")
    
    def final_category_menu(self, category_url, category_name):
        """Son kategori seçim menüsünü göster - ÇOKLU SEÇİM DESTEĞİ"""
        # Kategori sayfasına git
        if not self.go_to_selected_category(category_url):
            return
        
        # Alt kategorileri al
        sub_sub_categories = self.get_sub_sub_categories(category_url)
        
        # Seçili kategoriler listesi
        selected_categories = []
        
        while True:
            if sub_sub_categories:
                # Seçili kategorileri göster
                self.display_selected_categories(selected_categories)
                
                print(f"\n" + "="*50)
                print(f"🎯 {category_name.upper()} KATEGORİLERİ")
                print("="*50)
                max_option = self.display_menu(f"{category_name.upper()} ALT KATEGORİLERİ", sub_sub_categories, show_back=False, show_exit=False, selected_items=selected_categories)
                
                print(f"{max_option}. ➕ Çoklu Seçim İle Kategori Ekle")
                max_option += 1
                
                if selected_categories:
                    print(f"{max_option}. 🗑️  Seçili Kategorileri Temizle")
                    max_option += 1
                
                print(f"{max_option}. ✅ Seçimleri Tamamla ve Scraping'e Başla")
                max_option += 1
                
                print(f"{max_option}. ↩️ Üst menüye dön")
                max_option += 1
                
                print(f"{max_option}. 🚪 Çıkış")
                
                choice = self.get_user_choice(max_option)
                if choice is None:
                    continue
                
                # Menü seçeneklerini hesapla
                category_count = len(sub_sub_categories)
                add_option = category_count + 1
                clear_option = add_option + 1 if selected_categories else None
                if clear_option:
                    complete_option = clear_option + 1
                else:
                    complete_option = add_option + 1
                back_option = complete_option + 1
                exit_option = back_option + 1
                
                if 1 <= choice <= category_count:
                    # Tek kategori seçildi - direkt seçim
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
                        self.start_appropriate_scraper(final_url, category_name, selected_path)
                        input("\n⏎ Devam etmek için Enter'a basın...")
                        return
                    elif final_choice == 2:
                        return
                    else:
                        print("👋 Çıkış yapılıyor...")
                        exit()
                
                elif choice == add_option:
                    # Çoklu seçim yap
                    new_selections = self.multiple_category_selection_menu(sub_sub_categories)
                    if new_selections:
                        # Seçilen kategorileri ekle (duplikasyon kontrolü)
                        for new_cat in new_selections:
                            if new_cat not in selected_categories:
                                selected_categories.append(new_cat)
                        print(f"✅ Toplam {len(selected_categories)} kategori seçili")
                
                elif clear_option and choice == clear_option:
                    # Seçili kategorileri temizle
                    selected_categories.clear()
                    print("🗑️  Seçili kategoriler temizlendi")
                
                elif choice == complete_option:
                    # Seçimleri tamamla ve scraper başlat
                    if not selected_categories:
                        print("❌ Hiç kategori seçilmedi! Önce kategori seçin.")
                        continue
                    
                    print(f"\n✅ {len(selected_categories)} kategori için scraper başlatılıyor...")
                    for i, selected_cat in enumerate(selected_categories, 1):
                        selected_path = f"{category_name} → {selected_cat['name']}"
                        
                        # Belirgin tasarım ile göster
                        box_width = max(70, len(selected_path) + 10)
                        header_text = f"🎯 KATEGORİ {i}/{len(selected_categories)}"
                        path_text = f"📂 {selected_path}"
                        
                        print("\n" + "="*box_width)
                        print("│" + " "*(box_width-2) + "│")
                        
                        # Header
                        header_spaces = box_width - 4 - len(header_text)
                        print(f"│  {header_text}" + " "*header_spaces + "│")
                        print("│  " + "-"*(box_width-6) + "  │")
                        
                        # Path
                        path_spaces = box_width - 4 - len(path_text)
                        print(f"│  {path_text}" + " "*path_spaces + "│")
                        
                        print("│" + " "*(box_width-2) + "│")
                        print("="*box_width)
                        
                        final_url = selected_cat['url']
                        self.go_to_selected_category(final_url)
                        self.start_appropriate_scraper(final_url, category_name, selected_path)
                        
                        if i < len(selected_categories):
                            input("\n⏎ Sonraki kategoriye geçmek için Enter'a basın...")
                    
                    input("\n⏎ Devam etmek için Enter'a basın...")
                    return
                
                elif choice == back_option:
                    return
                
                elif choice == exit_option:
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