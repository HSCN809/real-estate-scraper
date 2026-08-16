import os
import time
import uuid

import pytest
import requests

API = os.getenv("SMOKE_API_URL", "http://127.0.0.1:8000")


def _api_up() -> bool:
    try:
        return requests.get(f"{API}/", timeout=3).status_code == 200
    except requests.RequestException:
        return False


pytestmark = pytest.mark.skipif(not _api_up(), reason="API not running")


def test_hepsiemlak_one_page_task_reaches_terminal_state():
    suffix = uuid.uuid4().hex[:8]
    session = requests.Session()
    created = session.post(
        f"{API}/api/v1/auth/register",
        json={
            "username": f"scrape_{suffix}",
            "email": f"scrape_{suffix}@example.com",
            "password": "SmokeTest1",
        },
        timeout=10,
    )
    assert created.status_code == 201, created.text

    started = session.post(
        f"{API}/api/v1/scrape/hepsiemlak",
        json={
            "listing_type": "satilik",
            "category": "konut",
            "cities": ["Bayburt"],
            "max_pages": 1,
            "scraping_method": "selenium",
            "proxy_enabled": True,
        },
        timeout=15,
    )
    assert started.status_code == 200, started.text
    task_id = started.json()["task_id"]
    assert task_id

    deadline = time.time() + 180
    last = {}
    while time.time() < deadline:
        status = session.get(f"{API}/api/v1/tasks/{task_id}", timeout=10)
        assert status.status_code == 200, status.text
        last = status.json()
        if last.get("status") in {"completed", "failed"}:
            break
        time.sleep(5)

    assert last.get("status") in {"completed", "failed"}, last
    assert last.get("task_id") == task_id
