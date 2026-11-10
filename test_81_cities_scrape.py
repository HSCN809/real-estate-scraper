"""
HepsiEmlak 81 İl Kazıma Test Scripti
Tüm 81 il için kiralık/satılık konut verilerini Go Invisible Proxy üzerinden çeker.
Cloudflare tespitini, başarı oranını ve çekilen ilan sayısını raporlar.
"""

import argparse
import json
import os
import random
import sys
import time
from datetime import datetime

# Backend modüllerini ekle
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(SCRIPT_DIR, "Backend"))

from python_proxy.go_proxy_client import CloudflareBypassClient
from scrapers.hepsiemlak.listings import extract_listings_from_html
from scrapers.hepsiemlak.urls import build_location_url, build_page_url

# Türkiye'nin resmi 81 ili (Alfabetik sıra)
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


def check_cloudflare_challenge(status_code: int, html_text: str) -> bool:
    """Cloudflare challenge/turnstile var mı kontrol et"""
    if status_code in (403, 503):
        return True
    lower_html = html_text.lower()
    challenge_indicators = [
        "cf-turnstile",
        "challenge-platform",
        "cf-challenge-running",
        "attention required! | cloudflare",
        "just a moment...",
    ]
    return any(ind in lower_html for ind in challenge_indicators)


def run_81_cities_scrape(
    listing_type: str = "kiralik",
    category: str = "konut",
    max_pages_per_city: int = 1,
    city_limit: int | None = None,
    delay_min: float = 2.0,
    delay_max: float = 3.5,
    proxy_url: str = "http://127.0.0.1:8080",
    output_dir: str = "outputs",
):
    print("=" * 70)
    print("HEPSIEMLAK 81 İL CLOUDFLARE VE KAZIMA TESTİ")
    print("=" * 70)
    print(f"Kategori          : {category.capitalize()} - {listing_type.capitalize()}")
    print(f"Şehir Başına Sayfa: {max_pages_per_city}")
    print(f"İstek Aralığı     : {delay_min:.1f}s - {delay_max:.1f}s (rastgele jitter)")
    print(f"Proxy Adresi      : {proxy_url}")
    print("=" * 70)

    # API Key env kontrolü
    if not os.getenv("PROXY_API_KEY"):
        os.environ["PROXY_API_KEY"] = "test-secret"

    client = CloudflareBypassClient(proxy_url=proxy_url)
    target_cities = TURKEY_81_CITIES[:city_limit] if city_limit else TURKEY_81_CITIES

    os.makedirs(output_dir, exist_ok=True)
    start_time = time.time()

    summary = {
        "start_time": datetime.now().isoformat(),
        "listing_type": listing_type,
        "category": category,
        "total_target_cities": len(target_cities),
        "successful_cities": 0,
        "failed_cities": 0,
        "cloudflare_blocked_cities": 0,
        "total_listings_scraped": 0,
        "city_results": {},
    }

    all_listings: list[dict] = []

    for idx, city in enumerate(target_cities, 1):
        city_start = time.time()
        base_city_url = build_location_url(city, listing_type, category)
        city_listings_count = 0
        city_status = "SUCCESS"
        city_pages_scraped = 0

        print(f"\n[{idx:2d}/{len(target_cities)}] {city:<14} -> Hedef: {base_city_url}")

        for page in range(1, max_pages_per_city + 1):
            page_url = build_page_url(base_city_url, page)
            try:
                resp = client.fetch_with_retry(page_url, max_retries=2)
                html_text = resp.body.decode("utf-8", errors="ignore") if resp.body else ""
                is_blocked = check_cloudflare_challenge(resp.status, html_text)

                if is_blocked:
                    print(f"    Sayfa {page}: [UYARI] Cloudflare Challenge/Engeli algılandı! (HTTP {resp.status})")
                    city_status = "CLOUDFLARE_BLOCKED"
                    summary["cloudflare_blocked_cities"] += 1
                    break

                if resp.status != 200:
                    print(f"    Sayfa {page}: [HATA] HTTP {resp.status} döndü.")
                    city_status = f"HTTP_{resp.status}"
                    break

                # İlanları ayıkla
                listings = extract_listings_from_html(
                    html_text,
                    page_url=page_url,
                    category=category,
                    city=city,
                    scraping_method="81_cities_test_proxy",
                )

                page_count = len(listings)
                city_listings_count += page_count
                city_pages_scraped += 1
                all_listings.extend(listings)

                print(f"    Sayfa {page}: 200 OK | {page_count:2d} ilan ayıklandı ({len(resp.body):,} byte)")

                # Eğer sayfada ilan yoksa sonraki sayfalara bakma
                if page_count == 0:
                    break

                # Sayfalar arası bekleme
                if page < max_pages_per_city:
                    sleep_time = random.uniform(delay_min, delay_max)
                    time.sleep(sleep_time)

            except Exception as e:
                print(f"    Sayfa {page}: [İSTİSNA] {e}")
                city_status = "EXCEPTION"
                break

        city_elapsed = time.time() - city_start
        if city_status == "SUCCESS":
            summary["successful_cities"] += 1
        else:
            summary["failed_cities"] += 1

        summary["total_listings_scraped"] += city_listings_count
        summary["city_results"][city] = {
            "status": city_status,
            "pages_scraped": city_pages_scraped,
            "listings_count": city_listings_count,
            "elapsed_seconds": round(city_elapsed, 2),
        }

        # Şehirler arası insan benzeri rastgele bekleme (jitter)
        if idx < len(target_cities):
            jitter = random.uniform(delay_min, delay_max)
            time.sleep(jitter)

    total_elapsed = time.time() - start_time
    summary["end_time"] = datetime.now().isoformat()
    summary["total_duration_seconds"] = round(total_elapsed, 2)

    # Sonuçları JSON olarak kaydet
    result_file = os.path.join(output_dir, f"hepsiemlak_81_il_ozet_{int(time.time())}.json")
    with open(result_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 70)
    print("GENEL TEST ÖZETİ")
    print("=" * 70)
    print(f"Toplam Hedef Şehir    : {len(target_cities)}")
    print(f"Başarılı Şehirler     : {summary['successful_cities']}")
    print(f"Hatalı/Engelli Şehir  : {summary['failed_cities']}")
    print(f"Cloudflare Engeli     : {summary['cloudflare_blocked_cities']}")
    print(f"Toplam Çekilen İlan   : {summary['total_listings_scraped']}")
    print(f"Toplam Süre           : {total_elapsed:.1f} saniye (~{total_elapsed/60:.1f} dakika)")
    print(f"Rapor Dosyası         : {result_file}")
    print("=" * 70)

    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="HepsiEmlak 81 İl Kazıma Testi")
    parser.add_argument("--type", default="kiralik", choices=["kiralik", "satilik"], help="İlan tipi")
    parser.add_argument("--category", default="konut", help="Kategori (varsayılan: konut)")
    parser.add_argument("--pages", type=int, default=1, help="Şehir başına taranacak maksimum sayfa (varsayılan: 1)")
    parser.add_argument("--limit", type=int, default=None, help="Yalnızca ilk N şehri test et (örn: --limit 5)")
    parser.add_argument("--delay-min", type=float, default=2.0, help="Minimum bekleme süresi (sn)")
    parser.add_argument("--delay-max", type=float, default=3.5, help="Maksimum bekleme süresi (sn)")
    parser.add_argument("--proxy-url", default="http://127.0.0.1:8080", help="Go Proxy URL")

    args = parser.parse_args()

    run_81_cities_scrape(
        listing_type=args.type,
        category=args.category,
        max_pages_per_city=args.pages,
        city_limit=args.limit,
        delay_min=args.delay_min,
        delay_max=args.delay_max,
        proxy_url=args.proxy_url,
    )
