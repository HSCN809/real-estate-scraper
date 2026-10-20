import os
import re
import time
import uuid

import pytest
import requests

SUPPORTED_SCRAPING_METHODS = (
    "scrapling_fetcher_session",
    "scrapling_spider_fetcher_session",
    "scrapling_dynamic_session",
    "scrapling_spider_dynamic_session",
    "scrapling_stealth_session",
    "scrapling_spider_stealth_session",
    "selenium",
)

API = os.getenv("SMOKE_API_URL", "http://127.0.0.1:8000")

TURKEY_CITIES = [
    "Adana",
    "Adıyaman",
    "Afyonkarahisar",
    "Ağrı",
    "Aksaray",
    "Amasya",
    "Ankara",
    "Antalya",
    "Ardahan",
    "Artvin",
    "Aydın",
    "Balıkesir",
    "Bartın",
    "Batman",
    "Bayburt",
    "Bilecik",
    "Bingöl",
    "Bitlis",
    "Bolu",
    "Burdur",
    "Bursa",
    "Çanakkale",
    "Çankırı",
    "Çorum",
    "Denizli",
    "Diyarbakır",
    "Düzce",
    "Edirne",
    "Elazığ",
    "Erzincan",
    "Erzurum",
    "Eskişehir",
    "Gaziantep",
    "Giresun",
    "Gümüşhane",
    "Hakkari",
    "Hatay",
    "Iğdır",
    "Isparta",
    "İstanbul",
    "İzmir",
    "Kahramanmaraş",
    "Karabük",
    "Karaman",
    "Kars",
    "Kastamonu",
    "Kayseri",
    "Kilis",
    "Kırıkkale",
    "Kırklareli",
    "Kırşehir",
    "Kocaeli",
    "Konya",
    "Kütahya",
    "Malatya",
    "Manisa",
    "Mardin",
    "Mersin",
    "Muğla",
    "Muş",
    "Nevşehir",
    "Niğde",
    "Ordu",
    "Osmaniye",
    "Rize",
    "Sakarya",
    "Samsun",
    "Siirt",
    "Sinop",
    "Sivas",
    "Şanlıurfa",
    "Şırnak",
    "Tekirdağ",
    "Tokat",
    "Trabzon",
    "Tunceli",
    "Uşak",
    "Van",
    "Yalova",
    "Yozgat",
    "Zonguldak",
]

PLATFORMS = ("hepsiemlak", "emlakjet")


def _api_up() -> bool:
    try:
        return requests.get(f"{API}/", timeout=3).status_code == 200
    except requests.RequestException:
        return False


pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(not _api_up(), reason="API not running"),
]


def _timeout_for(method: str) -> int:
    if method == "selenium" or "stealth" in method or "dynamic" in method:
        return int(os.getenv("SMOKE_BROWSER_TIMEOUT", "3600"))
    return int(os.getenv("SMOKE_FETCHER_TIMEOUT", "1200"))


def _auth_session() -> requests.Session:
    suffix = uuid.uuid4().hex[:8]
    session = requests.Session()
    created = session.post(
        f"{API}/api/v1/auth/register",
        json={
            "username": f"live_{suffix}",
            "email": f"live_{suffix}@example.com",
            "password": "SmokeTest1",
        },
        timeout=10,
    )
    assert created.status_code == 201, created.text
    return session


def _wait_task(session: requests.Session, task_id: str, timeout: int) -> dict:
    deadline = time.time() + timeout
    last: dict = {}
    while time.time() < deadline:
        response = session.get(f"{API}/api/v1/tasks/{task_id}", timeout=15)
        response.raise_for_status()
        last = response.json()
        if last.get("status") in {"completed", "failed"}:
            return last
        time.sleep(8)
    return last


def _listing_count(payload: dict) -> int:
    message = str(payload.get("message") or "")
    match = re.search(r"(\d+)\s+ilan", message)
    if match:
        return int(match.group(1))
    return 0


@pytest.mark.parametrize("platform", PLATFORMS)
@pytest.mark.parametrize("method", SUPPORTED_SCRAPING_METHODS)
def test_one_page_all_cities_live(platform: str, method: str):
    assert len(TURKEY_CITIES) == 81
    session = _auth_session()
    started = session.post(
        f"{API}/api/v1/scrape/{platform}",
        json={
            "listing_type": "satilik",
            "category": "konut",
            "cities": TURKEY_CITIES,
            "max_pages": 1,
            "scraping_method": method,
            "proxy_enabled": method != "selenium",
        },
        timeout=30,
    )
    assert started.status_code == 200, started.text
    task_id = started.json()["task_id"]
    result = _wait_task(session, task_id, _timeout_for(method))
    assert result.get("status") == "completed", result
    assert _listing_count(result) > 0, result
