import os
import sys
import json

sys.path.insert(0, r'c:\Users\ozenh\OneDrive\Desktop\Projelerim\real-estate-scraper\Backend')

from python_proxy.go_proxy_client import CloudflareBypassClient
from scrapers.hepsiemlak.listings import extract_listings_from_html
from scrapers.hepsiemlak.scrapling_scraper import HepsiemlakScraplingScraper

os.environ['PROXY_API_KEY'] = 'test-secret'
proxy_url = os.getenv('GO_PROXY_URL', 'http://127.0.0.1:8080')

print('=== Test 1: Fetch Search Page via CloudflareBypassClient ===')
client = CloudflareBypassClient(proxy_url=proxy_url)
target_url = 'https://www.hepsiemlak.com/kadikoy-satilik'

print(f'Fetching: {target_url}')
response = client.fetch_with_retry(target_url, max_retries=2)

print(f'Proxy response status: {response.status}')
print(f'Body size: {len(response.body)} bytes')

html_text = response.body.decode('utf-8', errors='ignore')

# Check Cloudflare challenge markers
has_turnstile = 'cf-turnstile' in html_text or 'challenge-platform' in html_text
print(f'Cloudflare challenge detected: {has_turnstile}')

# Extract listings
listings = extract_listings_from_html(html_text, page_url=target_url, category='konut', city='İstanbul', district='Kadıköy', scraping_method='go_proxy')
print(f'Extracted listings count: {len(listings)}')

if len(listings) == 0 or has_turnstile or response.status != 200:
    print('FAILURE: Search page scrape failed or got challenged')
    sys.exit(1)

for i, listing in enumerate(listings[:3], 1):
    link = listing.get('ilan_linki')
    title = listing.get('baslik')
    price = listing.get('fiyat')
    location = f"{listing.get('il')} / {listing.get('ilce')} / {listing.get('mahalle')}"
    room = listing.get('oda_sayisi')
    sqm = listing.get('metrekare')
    age = listing.get('bina_yasi')
    print(f"\n--- İlan #{i} ---")
    print(f"Başlık : {title}")
    print(f"Fiyat  : {price}")
    print(f"Konum  : {location}")
    print(f"Özellik: {room} | {sqm} | {age}")
    print(f"Link   : {link}")

# Test 2: Scrape single listing detail page
first_link = listings[0].get('ilan_linki')
print(f'\n=== Test 2: Fetch Single Listing Detail Page ===')
print(f'Detail URL: {first_link}')
detail_resp = client.fetch_with_retry(first_link, max_retries=2)
print(f'Detail status: {detail_resp.status}')
print(f'Detail size: {len(detail_resp.body)} bytes')

detail_html = detail_resp.body.decode('utf-8', errors='ignore')
detail_has_turnstile = 'cf-turnstile' in detail_html or 'challenge-platform' in detail_html
has_next_data = '__NEXT_DATA__' in detail_html
print(f'Detail challenge: {detail_has_turnstile}')
print(f'Detail has __NEXT_DATA__: {has_next_data}')

if detail_resp.status != 200 or detail_has_turnstile or len(detail_resp.body) < 10000:
    print('FAILURE: Detail page scrape failed or challenged')
    sys.exit(1)

# Test 3: Official HepsiemlakScraplingScraper pipeline with proxy_enabled=True
print(f'\n=== Test 3: Official HepsiemlakScraplingScraper with proxy_enabled=True ===')
scraper = HepsiemlakScraplingScraper(
    listing_type='satilik',
    category='konut',
    proxy_enabled=True,
    proxy_url=proxy_url,
)

selector = scraper.fetch_page(target_url)
if selector is None:
    print('FAILURE: HepsiemlakScraplingScraper.fetch_page returned None')
    sys.exit(1)

scraper_listings = extract_listings_from_html(
    selector.body.decode('utf-8', errors='ignore'),
    page_url=target_url,
    category='konut',
    city='İstanbul',
    district='Kadıköy',
    scraping_method='hepsiemlak_scrapling_scraper',
)
print(f'Scrapling scraper extracted listings: {len(scraper_listings)}')

if len(scraper_listings) == 0:
    print('FAILURE: Scrapling scraper extracted 0 listings')
    sys.exit(1)

print('\nSUCCESS: All real HepsiEmlak scrape tests passed completely without Cloudflare challenges!')
sys.exit(0)
