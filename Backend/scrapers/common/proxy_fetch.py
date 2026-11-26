"""Shared proxy-backed fetch helpers for scrapling scrapers."""

from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from contextlib import contextmanager
import os
import queue
import threading
import time
from typing import Any, Callable, Iterable, Iterator, TypeVar

from python_proxy.go_proxy_client import CloudflareBypassClient
from scrapling.parser import Selector

_T = TypeVar("_T")
_R = TypeVar("_R")
DEFAULT_PROXY_CONCURRENCY = max(
    1, min(6, int(os.getenv("SCRAPER_PROXY_CONCURRENCY", "3")))
)


def resolve_go_proxy_url(proxy_url: str | None = None) -> str:
    if proxy_url:
        return proxy_url

    default_url = "http://127.0.0.1:8080"
    if os.getenv("ENVIRONMENT") == "production":
        default_url = "http://invisible-proxy:8080"
    return os.getenv("GO_PROXY_URL", default_url)


_NON_RETRYABLE_STATUSES = frozenset({400, 401, 404, 410, 422})


def iter_bounded(
    items: Iterable[_T],
    fn: Callable[[_T], _R],
    *,
    max_workers: int = DEFAULT_PROXY_CONCURRENCY,
    stop_when: Callable[[], bool] | None = None,
) -> Iterator[tuple[_T, _R]]:
    """Run ``fn`` across items with a small worker window and yield on caller thread."""
    workers = max(1, int(max_workers or 1))
    item_list = list(items)
    if not item_list:
        return
    if workers == 1 or len(item_list) == 1:
        for item in item_list:
            if stop_when and stop_when():
                break
            yield item, fn(item)
        return

    item_iter = iter(item_list)
    with ThreadPoolExecutor(max_workers=min(workers, len(item_list))) as executor:
        in_flight: dict[Future[_R], _T] = {}

        def _fill_pool() -> None:
            while len(in_flight) < workers:
                if stop_when and stop_when():
                    break
                try:
                    nxt = next(item_iter)
                except StopIteration:
                    break
                in_flight[executor.submit(fn, nxt)] = nxt

        _fill_pool()
        while in_flight:
            done, _ = wait(in_flight.keys(), return_when=FIRST_COMPLETED)
            for fut in done:
                item = in_flight.pop(fut)
                yield item, fut.result()
            _fill_pool()


class ProxyFetchClient:
    """Thin adapter that fetches pages via Go proxy and returns scrapling Selectors."""

    def __init__(
        self,
        enabled: bool = False,
        proxy_url: str | None = None,
        user_agent: str | None = None,
        max_retries: int = 3,
        initial_delay: float = 1.5,
        max_delay: float = 6.0,
    ):
        self.enabled = enabled
        self.proxy_url = resolve_go_proxy_url(proxy_url)
        self.user_agent = user_agent
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self._owner_thread_id = threading.get_ident()
        self._worker_pool: queue.LifoQueue[CloudflareBypassClient] = queue.LifoQueue()
        self._closed = False
        self._clients_lock = threading.Lock()
        self._cooldown_lock = threading.Lock()
        self._cooldown_until = 0.0
        self._clients: list[CloudflareBypassClient] = []
        self.client = (
            CloudflareBypassClient(
                proxy_url=self.proxy_url,
                user_agent=user_agent,
                transport_retries=0,
            )
            if enabled
            else None
        )
        if self.client is not None:
            self._clients.append(self.client)

    def _borrow_worker_client(self) -> CloudflareBypassClient:
        try:
            return self._worker_pool.get_nowait()
        except queue.Empty:
            client = CloudflareBypassClient(
                proxy_url=self.proxy_url,
                user_agent=self.user_agent,
                transport_retries=0,
            )
            with self._clients_lock:
                self._clients.append(client)
            return client

    def _get_client(self) -> CloudflareBypassClient | None:
        if not self.enabled or self._closed:
            return None
        if threading.get_ident() == self._owner_thread_id:
            return self.client
        return self._borrow_worker_client()

    @contextmanager
    def _acquire_client(self) -> Iterator[CloudflareBypassClient | None]:
        if not self.enabled or self._closed:
            yield None
            return
        if threading.get_ident() == self._owner_thread_id:
            yield self.client
            return
        client = self._borrow_worker_client()
        try:
            yield client
        finally:
            if not self._closed:
                self._worker_pool.put(client)

    def close(self) -> None:
        self._closed = True
        while True:
            try:
                self._worker_pool.get_nowait()
            except queue.Empty:
                break
        with self._clients_lock:
            for client in self._clients:
                client.close()
            self._clients.clear()
        self.client = None

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

    @staticmethod
    def _retry_after_seconds(headers: dict[str, Any] | None) -> float | None:
        if not headers:
            return None
        for key, value in headers.items():
            if str(key).lower() == "retry-after":
                raw = value[0] if isinstance(value, (list, tuple)) and value else value
                try:
                    return max(1.0, min(30.0, float(str(raw).strip())))
                except (TypeError, ValueError):
                    return None
        return None

    def _wait_cooldown(self) -> None:
        with self._cooldown_lock:
            remaining = self._cooldown_until - time.monotonic()
        if remaining > 0:
            time.sleep(remaining)

    def _set_cooldown(self, delay: float) -> None:
        target = time.monotonic() + max(0.0, delay)
        with self._cooldown_lock:
            if target > self._cooldown_until:
                self._cooldown_until = target

    def fetch_selector(self, url: str, task_log=None) -> Selector | None:
        with self._acquire_client() as client:
            if not self.enabled or client is None:
                raise RuntimeError("ProxyFetchClient is not enabled")

            max_attempts = max(1, self.max_retries)
            last_error = "Proxy fetch failed"

            for attempt in range(max_attempts):
                self._wait_cooldown()
                response = client.fetch_with_retry(
                    url=url,
                    max_retries=1,
                    initial_delay=self.initial_delay,
                )

                rate_limited = False
                retry_after = None
                if response.error:
                    last_error = f"Proxy fetch failed ({response.status}): {response.error}"
                elif response.status >= 400:
                    last_error = f"Proxy returned status {response.status} for {url}"
                    if response.status in _NON_RETRYABLE_STATUSES:
                        break
                    if response.status in (429, 503):
                        rate_limited = True
                        retry_after = self._retry_after_seconds(response.headers)
                else:
                    body = response.body or b""
                    if len(body) <= 100:
                        last_error = (
                            f"Proxy response too short ({len(body)} bytes) for {url}"
                        )
                    else:
                        # Cloudflare challenge markers appear in document head / early body.
                        decoded = body[:16384].decode("utf-8", errors="ignore")
                        if self._is_cloudflare_challenge(decoded):
                            last_error = f"Cloudflare challenge still detected for {url}"
                            rate_limited = True
                        else:
                            return Selector(content=body, url=url)

                delay = (
                    retry_after
                    if retry_after is not None
                    else (
                        min(20.0, 5.0 * (2**attempt))
                        if rate_limited
                        else min(self.max_delay, self.initial_delay * (2**attempt))
                    )
                )
                if rate_limited:
                    self._set_cooldown(delay)

                if attempt < max_attempts - 1:
                    self._log(
                        task_log,
                        f"{last_error}; retrying in {delay:.1f}s (attempt {attempt + 1}/{max_attempts})",
                        level="warning",
                    )
                    if not rate_limited:
                        time.sleep(delay)

            self._log(task_log, last_error, level="warning")
            return None
