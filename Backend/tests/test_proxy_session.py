import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from python_proxy.go_proxy_client import (
    CloudflareBypassClient,
    GoProxyClient,
    ProxyResponse,
)


def test_get_cookies_returns_last_response_cookies():
    client = GoProxyClient()
    assert client.get_cookies() == []
    client._cookies = [{"Name": "__cf_bm", "Value": "token"}]
    assert client.get_cookies() == [{"Name": "__cf_bm", "Value": "token"}]


def test_fetch_with_retry_pins_proxy_session(monkeypatch):
    client = CloudflareBypassClient()
    seen = {}

    def fake_fetch(url, timeout=30, headers=None):
        seen["headers"] = headers
        return ProxyResponse(
            status=200,
            headers={},
            body=b"<html>listings</html>",
            cookies=[{"Name": "__cf_bm", "Value": "token"}],
        )

    monkeypatch.setattr(client.proxy_client, "fetch_page", fake_fetch)
    response = client.fetch_with_retry("https://www.hepsiemlak.com/", max_retries=1)

    assert response.status == 200
    assert seen["headers"]["X-Proxy-Session"] == client.session_id
    assert client.session_cookies["__cf_bm"] == "token"


def test_proxy_fetch_skips_retries_on_permanent_404(monkeypatch):
    from scrapers.common import proxy_fetch

    client = proxy_fetch.ProxyFetchClient(enabled=True, max_retries=5, initial_delay=2.0)
    calls = []
    sleeps = []

    def fake_fetch(url, max_retries=1, initial_delay=2.0):
        calls.append(url)
        return ProxyResponse(status=404, headers={}, body=b"Not Found")

    monkeypatch.setattr(client.client, "fetch_with_retry", fake_fetch)
    monkeypatch.setattr(proxy_fetch.time, "sleep", lambda s: sleeps.append(s))

    try:
        assert client.fetch_selector("https://www.hepsiemlak.com/missing") is None
        assert len(calls) == 1
        assert sleeps == []
    finally:
        client.close()


def test_proxy_fetch_uses_thread_local_clients_and_closes_all():
    import threading
    from concurrent.futures import ThreadPoolExecutor
    from scrapers.common import proxy_fetch

    client = proxy_fetch.ProxyFetchClient(enabled=True)
    main_c = client._get_client()
    assert main_c is client.client

    worker_clients = []
    lock = threading.Lock()

    def _grab():
        c = client._get_client()
        with lock:
            worker_clients.append(c)
        return id(c)

    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(lambda _: _grab(), range(4)))

    assert all(c is not None and c is not main_c for c in worker_clients)
    client.close()
    assert client.client is None
    assert client._clients == []


def test_iter_bounded_stops_early_and_caps_workers():
    import threading
    from scrapers.common.proxy_fetch import iter_bounded

    active = 0
    peak = 0
    lock = threading.Lock()
    processed = []

    def _work(item):
        nonlocal active, peak
        with lock:
            active += 1
            peak = max(peak, active)
        try:
            return item * 2
        finally:
            with lock:
                active -= 1

    stop = False
    for item, result in iter_bounded(
        range(10),
        _work,
        max_workers=2,
        stop_when=lambda: stop,
    ):
        processed.append((item, result))
        if len(processed) >= 2:
            stop = True

    assert peak <= 2
    assert len(processed) < 10


def test_proxy_fetch_shares_cooldown_on_429(monkeypatch):
    from scrapers.common import proxy_fetch

    client = proxy_fetch.ProxyFetchClient(enabled=True, max_retries=2, initial_delay=1.0)
    sleeps = []
    attempts = {"count": 0}

    def fake_fetch(url, max_retries=1, initial_delay=1.0):
        attempts["count"] += 1
        if attempts["count"] == 1:
            return ProxyResponse(
                status=429,
                headers={"Retry-After": "4"},
                body=b"Too Many Requests",
            )
        return ProxyResponse(status=200, headers={}, body=b"x" * 200)

    monkeypatch.setattr(client.client, "fetch_with_retry", fake_fetch)
    monkeypatch.setattr(proxy_fetch.time, "sleep", lambda s: sleeps.append(s))

    try:
        sel = client.fetch_selector("https://www.hepsiemlak.com/istanbul-kiralik")
        assert sel is not None
        assert attempts["count"] == 2
        assert any(3.5 <= s <= 4.1 for s in sleeps)
    finally:
        client.close()
