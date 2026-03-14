"""
Go Proxy Client - Cloudflare Bypass Client
Python client for the Invisible Go Proxy server
"""

import base64
import binascii
import json
import requests
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict

@dataclass
class ProxyRequest:
    """Request structure for Go proxy"""
    url: str
    method: str = "GET"
    headers: Optional[Dict[str, str]] = None
    body: Optional[bytes] = None
    timeout: int = 30

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ProxyResponse:
    """Response structure from Go proxy"""
    status: int
    headers: Dict[str, str]
    body: bytes
    cookies: Optional[List[Dict[str, Any]]] = None
    status_code: Optional[str] = None
    error: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProxyResponse':
        raw_body = data.get('body', b'')
        if isinstance(raw_body, str):
            try:
                body = base64.b64decode(raw_body, validate=True)
            except (binascii.Error, ValueError):
                body = raw_body.encode()
        else:
            body = raw_body

        return cls(
            status=data.get('status'),
            headers=data.get('headers', {}),
            body=body,
            cookies=data.get('cookies'),
            status_code=data.get('status_code'),
            error=data.get('error')
        )


class GoProxyClient:
    """
    Client for the Invisible Go Proxy server
    Provides Cloudflare bypass functionality with TLS fingerprint spoofing
    """

    def __init__(
        self,
        proxy_url: str = "http://127.0.0.1:8080",
        timeout: int = 30,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ):
        """
        Initialize the Go proxy client

        Args:
            proxy_url: URL of the Go proxy server (default: http://127.0.0.1:8080)
            timeout: Default timeout for requests in seconds
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds
        """
        self.proxy_url = proxy_url.rstrip('/')
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    def _make_proxy_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, str]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> ProxyResponse:
        """
        Make a request to the Go proxy server with retry logic

        Args:
            method: HTTP method (GET, POST)
            endpoint: Proxy endpoint (usually 'proxy')
            data: Request body data (for POST)
            params: Query parameters (for GET)

        Returns:
            ProxyResponse object
        """
        url = f"{self.proxy_url}/{endpoint}"
        last_error = None

        for attempt in range(self.max_retries + 1):
            try:
                if method == "GET":
                    response = requests.get(
                        url,
                        params=params,
                        headers=headers,
                        timeout=self.timeout
                    )
                else:  # POST
                    response = requests.post(
                        url,
                        json=data,
                        headers=headers,
                        timeout=self.timeout
                    )

                response_data = response.json()
                return ProxyResponse.from_dict(response_data)

            except requests.exceptions.RequestException as e:
                last_error = e
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay)
                    continue
                else:
                    # All retries failed, return error response
                    return ProxyResponse(
                        status=500,
                        headers={},
                        body=b'',
                        error=f"Proxy connection failed: {str(e)}"
                    )
            except json.JSONDecodeError as e:
                last_error = e
                return ProxyResponse(
                    status=500,
                    headers={},
                    body=b'',
                    error=f"Invalid proxy response: {str(e)}"
                )

    def get(self, url: str, headers: Optional[Dict[str, str]] = None) -> ProxyResponse:
        """
        Make a GET request through the Go proxy

        Args:
            url: Target URL
            headers: Optional headers to forward

        Returns:
            ProxyResponse object
        """
        return self._make_proxy_request(
            method="GET",
            endpoint="proxy",
            params={"url": url},
            headers=headers,
        )

    def post(
        self,
        url: str,
        body: Optional[bytes] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> ProxyResponse:
        """
        Make a POST request through the Go proxy

        Args:
            url: Target URL
            body: Request body
            headers: Optional headers to forward

        Returns:
            ProxyResponse object
        """
        request = ProxyRequest(
            url=url,
            method="POST",
            headers=headers,
            body=body
        )
        return self._make_proxy_request(
            method="POST",
            endpoint="proxy",
            data=request.to_dict()
        )

    def fetch_page(
        self,
        url: str,
        timeout: int = 30,
        headers: Optional[Dict[str, str]] = None,
    ) -> ProxyResponse:
        """
        Fetch a page through the Go proxy with automatic retry

        Args:
            url: Target URL to fetch
            timeout: Request timeout in seconds
            headers: Optional headers to forward

        Returns:
            ProxyResponse object
        """
        request = ProxyRequest(
            url=url,
            method="GET",
            headers=headers,
            timeout=timeout
        )
        return self._make_proxy_request(
            method="POST",
            endpoint="proxy",
            data=request.to_dict(),
        )

    def health_check(self) -> bool:
        """
        Check if the Go proxy server is healthy

        Returns:
            True if server is healthy, False otherwise
        """
        try:
            response = requests.get(f"{self.proxy_url}/", timeout=5)
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False

    def get_cookies(self) -> List[Dict[str, Any]]:
        """
        Get cookies from the last response
        """
        # This would need to be implemented with state tracking
        return []

    def __repr__(self) -> str:
        return f"GoProxyClient(proxy_url='{self.proxy_url}', timeout={self.timeout})"


class CloudflareBypassClient:
    """
    High-level client specifically designed for Cloudflare bypass
    Wraps GoProxyClient with additional anti-bot features
    """

    def __init__(
        self,
        proxy_url: str = "http://127.0.0.1:8080",
        user_agent: Optional[str] = None
    ):
        """
        Initialize the Cloudflare bypass client

        Args:
            proxy_url: URL of the Go proxy server
            user_agent: Custom user agent string
        """
        self.proxy_client = GoProxyClient(proxy_url=proxy_url)
        self.user_agent = user_agent or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

        # Store cookies for session persistence
        self.session_cookies = {}

    def fetch_with_retry(
        self,
        url: str,
        max_retries: int = 5,
        initial_delay: float = 2.0
    ) -> ProxyResponse:
        """
        Fetch a URL with intelligent retry logic for Cloudflare challenges

        Args:
            url: Target URL
            max_retries: Maximum number of retries
            initial_delay: Initial delay between retries (exponential backoff)

        Returns:
            ProxyResponse object
        """
        for attempt in range(max_retries):
            try:
                # Add session cookies if available
                headers = {"User-Agent": self.user_agent}
                if self.session_cookies:
                    headers["Cookie"] = "; ".join(f"{k}={v}" for k, v in self.session_cookies.items())

                response = self.proxy_client.fetch_page(url, headers=headers)

                # Always persist cookies (Cloudflare frequently sets tokens on 403 challenge responses)
                if response.cookies:
                    for cookie in response.cookies:
                        if isinstance(cookie, dict):
                            name = cookie.get('name') or cookie.get('Name') or ''
                            value = cookie.get('value') or cookie.get('Value') or ''
                            if name:
                                self.session_cookies[name] = value

                # Check if successful
                if response.status == 200 and response.error is None:
                    return response

                # Check for Cloudflare challenge (usually 403 or 503)
                if response.status in [403, 503]:
                    if attempt < max_retries - 1:
                        delay = initial_delay * (2 ** attempt)  # Exponential backoff
                        print(f"Cloudflare challenge detected, retrying in {delay:.1f}s (attempt {attempt + 1}/{max_retries})")
                        time.sleep(delay)
                        continue

                # Other error, return as is
                return response

            except Exception as e:
                if attempt < max_retries - 1:
                    delay = initial_delay * (2 ** attempt)
                    print(f"Request failed: {str(e)}, retrying in {delay:.1f}s (attempt {attempt + 1}/{max_retries})")
                    time.sleep(delay)
                    continue

                # All retries failed
                return ProxyResponse(
                    status=500,
                    headers={},
                    body=b'',
                    error=f"All retries failed: {str(e)}"
                )

        return ProxyResponse(
            status=500,
            headers={},
            body=b'',
            error="Maximum retries exceeded"
        )


def test_proxy_client():
    """Test the proxy client with a sample request (Docker compatible)"""
    print("🧪 Testing Go Proxy Client...")

    # Determine proxy URL based on environment
    import os
    proxy_url = os.getenv("GO_PROXY_URL", "http://127.0.0.1:8080")

    # In Docker, use the service name
    if os.getenv("ENVIRONMENT") == "production":
        proxy_url = os.getenv("GO_PROXY_URL", "http://invisible-proxy:8080")

    print(f"🔗 Using proxy URL: {proxy_url}")

    # Create client
    client = GoProxyClient(proxy_url=proxy_url)

    # Health check
    if not client.health_check():
        print("❌ Proxy server is not running.")
        print("   Start it with: docker-compose up invisible-proxy")
        return

    print("✅ Proxy server is running")

    # Test request
    response = client.fetch_page("https://httpbin.org/user-agent")

    if response.status == 200:
        print("✅ Proxy test successful!")
        print(f"Response status: {response.status}")
        print(f"Response length: {len(response.body)} bytes")
    else:
        print(f"❌ Proxy test failed: {response.error}")


if __name__ == "__main__":
    test_proxy_client()
