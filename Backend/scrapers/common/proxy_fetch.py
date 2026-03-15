# -*- coding: utf-8 -*-
"""Shared proxy-backed fetch helpers for scrapling scrapers."""

import os
import time
from typing import Optional

from scrapling.parser import Selector

from python_proxy.go_proxy_client import CloudflareBypassClient


def resolve_go_proxy_url(proxy_url: Optional[str] = None) -> str:
    if proxy_url:
        return proxy_url

    default_url = "http://127.0.0.1:8080"
    if os.getenv("ENVIRONMENT") == "production":
        default_url = "http://invisible-proxy:8080"
    return os.getenv("GO_PROXY_URL", default_url)


class ProxyFetchClient:
    """Thin adapter that fetches pages via Go proxy and returns scrapling Selectors."""

    def __init__(
        self,
        enabled: bool = False,
        proxy_url: Optional[str] = None,
        user_agent: Optional[str] = None,
        max_retries: int = 5,
        initial_delay: float = 2.0,
    ):
        self.enabled = enabled
        self.proxy_url = resolve_go_proxy_url(proxy_url)
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.client = CloudflareBypassClient(
            proxy_url=self.proxy_url,
            user_agent=user_agent,
        ) if enabled else None

    @staticmethod
    def _is_cloudflare_challenge(body_text: str) -> bool:
        page = (body_text or "").lower()
        markers = (
            "cf-challenge",
            "challenge-platform",
            "just a moment",
            "checking your browser",
            "attention required",
            "cf-turnstile",
            "/cdn-cgi/challenge-platform/",
        )
        return any(marker in page for marker in markers)

    @staticmethod
    def _log(task_log, message: str, level: str = "info") -> None:
        if not task_log:
            return
        if hasattr(task_log, "line"):
            task_log.line(message, level=level)
            return
        getattr(task_log, level, task_log.info)(message)

    def fetch_selector(self, url: str, task_log=None) -> Optional[Selector]:
        if not self.enabled or self.client is None:
            raise RuntimeError("ProxyFetchClient is not enabled")

        max_attempts = max(1, self.max_retries)
        last_error = "Proxy fetch failed"

        for attempt in range(max_attempts):
            response = self.client.fetch_with_retry(
                url=url,
                max_retries=1,
                initial_delay=self.initial_delay,
            )

            if response.error:
                last_error = f"Proxy fetch failed ({response.status}): {response.error}"
            elif response.status >= 400:
                last_error = f"Proxy returned status {response.status} for {url}"
            else:
                body = response.body or b""
                if len(body) <= 100:
                    last_error = f"Proxy response too short ({len(body)} bytes) for {url}"
                else:
                    decoded = body.decode("utf-8", errors="ignore")
                    if self._is_cloudflare_challenge(decoded):
                        last_error = f"Cloudflare challenge still detected for {url}"
                    else:
                        return Selector(content=body, url=url)

            if attempt < max_attempts - 1:
                delay = self.initial_delay * (2 ** attempt)
                self._log(
                    task_log,
                    f"{last_error}; retrying in {delay:.1f}s (attempt {attempt + 1}/{max_attempts})",
                    level="warning",
                )
                time.sleep(delay)

        self._log(task_log, last_error, level="warning")
        return None
