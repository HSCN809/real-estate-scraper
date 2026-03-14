# -*- coding: utf-8 -*-
"""Shared proxy-backed fetch helpers for scrapling scrapers."""

import os
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

        response = self.client.fetch_with_retry(
            url=url,
            max_retries=self.max_retries,
            initial_delay=self.initial_delay,
        )

        if response.error:
            self._log(
                task_log,
                f"Proxy fetch failed ({response.status}): {response.error}",
                level="warning",
            )
            return None

        if response.status >= 400:
            self._log(
                task_log,
                f"Proxy returned status {response.status} for {url}",
                level="warning",
            )
            return None

        body = response.body or b""
        if len(body) <= 100:
            self._log(
                task_log,
                f"Proxy response too short ({len(body)} bytes) for {url}",
                level="warning",
            )
            return None

        decoded = body.decode("utf-8", errors="ignore")
        if self._is_cloudflare_challenge(decoded):
            self._log(
                task_log,
                f"Cloudflare challenge still detected for {url}",
                level="warning",
            )
            return None

        return Selector(content=body, url=url)
