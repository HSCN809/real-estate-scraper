"""Invisible Go Proxy smoke tests (SSRF allowlist aware)."""

import os
import sys
import time

import requests

if os.getenv("ENVIRONMENT") == "production":
    PROXY_URL = os.getenv("GO_PROXY_URL", "http://invisible-proxy:8080")
else:
    PROXY_URL = os.getenv("GO_PROXY_URL", "http://127.0.0.1:8080")

ALLOWED_URL = "https://www.hepsiemlak.com"
API_KEY = os.getenv("PROXY_API_KEY", "").strip()
HEADERS = {"X-API-Key": API_KEY} if API_KEY else {}
BLOCKED_URLS = [
    "https://httpbin.org/get",
    "http://127.0.0.1:9/",
    "https://example.com",
]


def test_health_check() -> bool:
    response = requests.get(f"{PROXY_URL}/", timeout=5)
    if response.status_code != 200:
        print(f"FAIL health: {response.status_code}")
        return False
    print("PASS health")
    return True


def test_blocked_hosts() -> bool:
    ok = True
    for url in BLOCKED_URLS:
        response = requests.get(
            f"{PROXY_URL}/proxy", params={"url": url}, headers=HEADERS, timeout=10
        )
        if response.status_code != 400:
            print(f"FAIL allowlist {url}: {response.status_code}")
            ok = False
        else:
            print(f"PASS allowlist blocked {url}")
    return ok


def test_allowed_host() -> bool:
    started = time.time()
    response = requests.post(
        f"{PROXY_URL}/proxy",
        json={"url": ALLOWED_URL, "method": "GET", "timeout": 60},
        headers=HEADERS,
        timeout=65,
    )
    elapsed = time.time() - started
    if response.status_code != 200:
        print(f"FAIL allowed host: {response.status_code}")
        return False
    payload = response.json()
    print(f"PASS allowed host status={payload.get('status')} time={elapsed:.2f}s")
    return True


def main() -> int:
    print(f"proxy={PROXY_URL}")
    if not test_health_check():
        return 1
    blocked_ok = test_blocked_hosts()
    allowed_ok = test_allowed_host()
    return 0 if blocked_ok and allowed_ok else 1


if __name__ == "__main__":
    sys.exit(main())
