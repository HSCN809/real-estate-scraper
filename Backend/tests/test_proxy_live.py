import os

import pytest
import requests

PROXY = os.getenv("SMOKE_PROXY_URL", "http://127.0.0.1:8080")


def _proxy_up() -> bool:
    try:
        return requests.get(f"{PROXY}/", timeout=3).status_code == 200
    except requests.RequestException:
        return False


pytestmark = pytest.mark.skipif(not _proxy_up(), reason="Go proxy not running")


def test_proxy_health():
    response = requests.get(f"{PROXY}/", timeout=5)
    assert response.status_code == 200
    assert response.json()["service"] == "invisible-proxy"


def test_proxy_missing_url_is_rejected():
    response = requests.get(f"{PROXY}/proxy", timeout=5)
    assert response.status_code == 400


def test_proxy_does_not_succeed_on_closed_loopback():
    response = requests.get(
        f"{PROXY}/proxy",
        params={"url": "http://127.0.0.1:9/"},
        timeout=20,
    )
    assert response.status_code == 400
    assert "allowed" in response.text.lower() or "https" in response.text.lower()
