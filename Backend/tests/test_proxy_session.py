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
