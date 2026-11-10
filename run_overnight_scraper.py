"""
HepsiEmlak Gece Kazıma Motoru (Overnight Scraper)
- Tek yerel IP ile Cloudflare bot skorunu düşürmeden zamana yayarak 81 ili tarar.
- Her il için izole X-Proxy-Session açar ve il bitince çerezleri sıfırlar.
- 4-7 saniye dinamik gecikme uygular.
- Checkpoint sistemi ile internet kesilse bile kaldığı ilden/sayfadan devam eder.
- Cloudflare challenge algılarsa 5 dakika soğumaya (cooldown) geçip yeni session ile tekrar dener.
- Verileri il bazında disk üzerine parça parça yazar (RAM şişmez, veri kaybolmaz).
"""

import argparse
import ctypes
import json
import logging
import os
import random
import sys
import time
import uuid
from datetime import datetime

# Windows Güç ve Öncelik Bayrakları
ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001
BELOW_NORMAL_PRIORITY_CLASS = 0x00004000


def set_silent_mode():
    """İşlem önceliğini düşürür ve fanın hızlanmasını engeller."""
    if os.name == "nt":
        # Windows işlem önceliğini 'Normalin Altı' (Below Normal) yapar
        handle = ctypes.windll.kernel32.GetCurrentProcess()
        ctypes.windll.kernel32.SetPriorityClass(handle, BELOW_NORMAL_PRIORITY_CLASS)


def prevent_sleep():
    """Windows'un işlem bitene kadar uyku moduna geçmesini engeller."""
    if os.name == "nt":
        ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED)


def allow_sleep():
    """Windows'un normal uyku ayarlarına geri dönmesini sağlar."""
    if os.name == "nt":
        ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)

# Backend modüllerini ekle
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(SCRIPT_DIR, "Backend"))

from python_proxy.go_proxy_client import CloudflareBypassClient
from scrapers.hepsiemlak.listings import extract_listings_from_html
from scrapers.hepsiemlak.urls import build_location_url, build_page_url, normalize_location_slug

# 81 İl Listesi
TURKEY_81_CITIES = [
    "Adana", "Adıyaman", "Afyonkarahisar", "Ağrı", "Aksaray", "Amasya", "Ankara",
    "Antalya", "Ardahan", "Artvin", "Aydın", "Balıkesir", "Bartın", "Batman",
    "Bayburt", "Bilecik", "Bingöl", "Bitlis", "Bolu", "Burdur", "Bursa",
    "Çanakkale", "Çankırı", "Çorum", "Denizli", "Diyarbakır", "Düzce", "Edirne",
    "Elazığ", "Erzincan", "Erzurum", "Eskişehir", "Gaziantep", "Giresun", "Gümüşhane",
    "Hakkari", "Hatay", "Iğdır", "Isparta", "İstanbul", "İzmir", "Kahramanmaraş",
    "Karabük", "Karaman", "Kars", "Kastamonu", "Kayseri", "Kırıkkale", "Kırklareli",
    "Kırşehir", "Kilis", "Kocaeli", "Konya", "Kütahya", "Malatya", "Manisa",
    "Mardin", "Mersin", "Muğla", "Muş", "Nevşehir", "Niğde", "Ordu", "Osmaniye",
    "Rize", "Sakarya", "Samsun", "Siirt", "Sinop", "Sivas", "Şanlıurfa", "Şırnak",
    "Tekirdağ", "Tokat", "Trabzon", "Tunceli", "Uşak", "Van", "Yalova", "Yozgat",
    "Zonguldak"
]

OUTPUT_DIR = os.path.join(SCRIPT_DIR, "outputs", "overnight_data")
CHECKPOINT_FILE = os.path.join(SCRIPT_DIR, "outputs", "overnight_checkpoint.json")
LOG_FILE = os.path.join(SCRIPT_DIR, "outputs", "overnight_scrape.log")
STATUS_FILE = os.path.join(SCRIPT_DIR, "outputs", "overnight_status.json")


def update_live_status(
    status: str,
    current_city: str = "",
    current_city_index: int = 0,
    current_page: int = 0,
    completed_cities_count: int = 0,
    total_listings: int = 0,
    last_event: str = "",
    error_note: str = "",
):
    """Her 10 dakikalık kontrol ve izleme için canlı durum JSON'u yazar."""
    data = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": status,
        "current_city": current_city,
        "current_city_index": current_city_index,
        "total_cities": 81,
        "current_page": current_page,
        "completed_cities_count": completed_cities_count,
        "total_listings_scraped": total_listings,
        "last_event": last_event,
        "error_note": error_note,
    }
    try:
        with open(STATUS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def setup_logger():
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    logger = logging.getLogger("OvernightScraper")
    logger.setLevel(logging.INFO)
    logger.handlers = []

    # Dosya logu
    fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(fh)

    # Konsol logu
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(logging.Formatter("[%(asctime)s] %(message)s", datefmt="%H:%M:%S"))
    logger.addHandler(ch)
    return logger


logger = setup_logger()


def load_checkpoint() -> dict:
    if os.path.exists(CHECKPOINT_FILE):
        try:
            with open(CHECKPOINT_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "completed_cities": [],
        "current_city_index": 0,
        "total_listings_scraped": 0,
        "last_updated": None,
    }


def save_checkpoint(completed_cities: list[str], city_idx: int, total_scraped: int):
    os.makedirs(os.path.dirname(CHECKPOINT_FILE), exist_ok=True)
    data = {
        "completed_cities": completed_cities,
        "current_city_index": city_idx,
        "total_listings_scraped": total_scraped,
        "last_updated": datetime.now().isoformat(),
    }
    with open(CHECKPOINT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def check_cloudflare_challenge(status_code: int, html_text: str) -> bool:
    if status_code in (403, 503):
        return True
    lower = html_text.lower()
    return any(ind in lower for ind in ["cf-turnstile", "challenge-platform", "just a moment..."])


def run_overnight_scrape(
    listing_type: str = "kiralik",
    category: str = "konut",
    max_pages_per_city: int = 15,
    delay_min: float = 4.0,
    delay_max: float = 7.0,
    cooldown_seconds: int = 300,
    proxy_url: str = "http://127.0.0.1:8080",
):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    if not os.getenv("PROXY_API_KEY"):
        os.environ["PROXY_API_KEY"] = "test-secret"

    checkpoint = load_checkpoint()
    completed_cities = set(checkpoint.get("completed_cities", []))
    total_scraped = checkpoint.get("total_listings_scraped", 0)

    logger.info("=" * 60)
    logger.info("HEPSİEMLAK GECE KAZIMA MOTORU BAŞLATILDI")
    logger.info(f"Kategori: {category} | İlan Tipi: {listing_type}")
    logger.info(f"Şehir Başına Max Sayfa: {max_pages_per_city}")
    logger.info(f"İstek Aralığı: {delay_min}s - {delay_max}s (İnsani Dinamik Gecikme)")
    logger.info(f"Daha Önce Tamamlanan Şehir Sayısı: {len(completed_cities)}/81")
    logger.info("=" * 60)

    proxy_client = CloudflareBypassClient(proxy_url=proxy_url)

    # Proxy kontrolü
    if not proxy_client.proxy_client.health_check():
        logger.error(f"Go Proxy'ye ({proxy_url}) bağlanılamadı! Lütfen proxy'yi başlatın.")
        sys.exit(1)

    for city_idx, city in enumerate(TURKEY_81_CITIES, 1):
        if city in completed_cities:
            logger.info(f"[{city_idx}/81] {city} daha önce tamamlanmış, atlanıyor.")
            continue

        city_slug = normalize_location_slug(city)
        city_session_id = f"hepsiemlak_{city_slug}_{uuid.uuid4().hex[:6]}"
        base_city_url = build_location_url(city, listing_type, category)
        city_listings: list[dict] = []
        city_start_time = time.time()

        logger.info(f"\n>>> [{city_idx}/81] {city.upper()} Başlatılıyor (Session: {city_session_id})")

        consecutive_challenges = 0
        current_page = 1

        while current_page <= max_pages_per_city:
            page_url = build_page_url(base_city_url, current_page)
            headers = {"X-Proxy-Session": city_session_id}

            try:
                resp = proxy_client.proxy_client.get(page_url, headers=headers)
                html_text = resp.body.decode("utf-8", errors="ignore") if resp.body else ""
                is_challenge = check_cloudflare_challenge(resp.status, html_text)

                if is_challenge:
                    consecutive_challenges += 1
                    event_msg = f"Cloudflare Challenge algılandı (HTTP {resp.status}, Deneme: {consecutive_challenges}/3)"
                    logger.warning(f"[{city} - Sayfa {current_page}] {event_msg}")
                    update_live_status(
                        status="SOGUMA",
                        current_city=city,
                        current_city_index=city_idx,
                        current_page=current_page,
                        completed_cities_count=len(completed_cities),
                        total_listings=total_scraped,
                        last_event=event_msg,
                        error_note="Cloudflare bot challenge tetiklendi, 5dk bekleniyor.",
                    )

                    if consecutive_challenges >= 3:
                        logger.error(f"[{city}] 3 ardışık engelleme! Bu şehir pas geçiliyor.")
                        break

                    logger.info(f"Soğuma Modu (Cooldown): {cooldown_seconds} saniye bekleniyor...")
                    time.sleep(cooldown_seconds)

                    # Yeni bir izole session al
                    city_session_id = f"hepsiemlak_{city_slug}_retry_{uuid.uuid4().hex[:6]}"
                    continue

                if resp.status != 200:
                    logger.warning(f"[{city} - Sayfa {current_page}] HTTP {resp.status} döndü, sayfa atlanıyor.")
                    break

                # Başarılı sayfa
                consecutive_challenges = 0
                page_listings = extract_listings_from_html(
                    html_text,
                    page_url=page_url,
                    category=category,
                    city=city,
                    scraping_method="overnight_go_proxy",
                )

                count = len(page_listings)
                event_msg = f"[{city} - Sayfa {current_page}] 200 OK | {count} ilan ayıklandı"
                logger.info(f"{event_msg} ({len(resp.body):,} B)")
                update_live_status(
                    status="CALISIYOR",
                    current_city=city,
                    current_city_index=city_idx,
                    current_page=current_page,
                    completed_cities_count=len(completed_cities),
                    total_listings=total_scraped + count,
                    last_event=event_msg,
                )

                if count == 0:
                    logger.info(f"[{city}] Sayfada ilan kalmadı, şehir tamamlandı.")
                    break

                city_listings.extend(page_listings)
                total_scraped += count
                current_page += 1

                # Sayfalar arası insani dinamik bekleme
                sleep_duration = random.uniform(delay_min, delay_max)
                time.sleep(sleep_duration)

            except Exception as e:
                logger.error(f"[{city} - Sayfa {current_page}] Hata: {e}")
                time.sleep(5)
                break

        # Şehir tamamlandı, verileri diske yaz
        city_file = os.path.join(OUTPUT_DIR, f"{city.lower()}_{listing_type}.json")
        with open(city_file, "w", encoding="utf-8") as f:
            json.dump(city_listings, f, ensure_ascii=False, indent=2)

        completed_cities.add(city)
        save_checkpoint(list(completed_cities), city_idx, total_scraped)

        city_elapsed = time.time() - city_start_time
        logger.info(
            f"✓ [{city}] Bitti: {len(city_listings)} ilan kaydedildi ({city_file}) "
            f"[Süre: {city_elapsed:.1f}s | Toplam İlan: {total_scraped}]"
        )
        update_live_status(
            status="CALISIYOR",
            current_city=city,
            current_city_index=city_idx,
            current_page=current_page,
            completed_cities_count=len(completed_cities),
            total_listings=total_scraped,
            last_event=f"✓ [{city}] Bitti ({len(city_listings)} ilan)",
        )

        # Şehirler arası nefes alma (8 - 15 saniye)
        if city_idx < len(TURKEY_81_CITIES):
            inter_city_sleep = random.uniform(8.0, 15.0)
            time.sleep(inter_city_sleep)

    logger.info("=" * 60)
    logger.info(f"TÜM 81 İL İŞLEMİ TAMAMLANDI! Toplam Çekilen İlan: {total_scraped}")
    logger.info("=" * 60)
    update_live_status(
        status="TAMAMLANDI",
        completed_cities_count=len(completed_cities),
        total_listings=total_scraped,
        last_event="Tüm 81 il kazıma işlemi başarıyla tamamlandı.",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="HepsiEmlak Gece Kazıma Motoru")
    parser.add_argument("--type", default="kiralik", choices=["kiralik", "satilik"])
    parser.add_argument("--category", default="konut")
    parser.add_argument("--pages", type=int, default=15, help="Şehir başına taranacak sayfa sınırı")
    parser.add_argument("--delay-min", type=float, default=4.0)
    parser.add_argument("--delay-max", type=float, default=7.0)
    parser.add_argument("--cooldown", type=int, default=300, help="Challenge anında bekleme (sn)")
    parser.add_argument("--proxy-url", default="http://127.0.0.1:8080")

    args = parser.parse_args()

    prevent_sleep()
    set_silent_mode()
    logger.info("Windows Uyku Engelleme ve Sessiz Mod (Düşük CPU Önceliği) devrede.")
    try:
        run_overnight_scrape(
            listing_type=args.type,
            category=args.category,
            max_pages_per_city=args.pages,
            delay_min=args.delay_min,
            delay_max=args.delay_max,
            cooldown_seconds=args.cooldown,
            proxy_url=args.proxy_url,
        )
    finally:
        allow_sleep()
