"""Login/register rate limit behaviour."""

import os
import sys

import pytest
from fastapi import HTTPException

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from auth import router as auth_router

from tests.fake_task_redis import FakeRedis


def test_rate_limit_blocks_after_max_attempts(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(auth_router, "get_redis_client", lambda: fake)

    for _ in range(3):
        auth_router._enforce_rate_limit("rate:test", (3, 60))

    with pytest.raises(HTTPException) as exc_info:
        auth_router._enforce_rate_limit("rate:test", (3, 60))
    assert exc_info.value.status_code == 429
    assert exc_info.value.headers == {"Retry-After": "60"}

    # Farklı anahtar (başka IP/kullanıcı) etkilenmez.
    auth_router._enforce_rate_limit("rate:other", (3, 60))


def test_rate_limit_fails_open_when_redis_unavailable(monkeypatch):
    def unavailable():
        raise ConnectionError("redis down")

    monkeypatch.setattr(auth_router, "get_redis_client", unavailable)

    auth_router._enforce_rate_limit("rate:test", (0, 60))
