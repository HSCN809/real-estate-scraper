"""/health endpoint: DB ve Redis durumunu raporlar."""

import os
import sys
from contextlib import contextmanager
from types import SimpleNamespace

from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import main


class FakeEngine:
    def __init__(self, fail=False):
        self.fail = fail

    @contextmanager
    def connect(self):
        if self.fail:
            raise ConnectionError("db down")
        yield SimpleNamespace(execute=lambda _stmt: None)


def test_health_ok(monkeypatch):
    monkeypatch.setattr(main, "engine", FakeEngine())
    monkeypatch.setattr(main, "get_redis_client", lambda: SimpleNamespace(ping=lambda: True))

    response = TestClient(main.app).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok", "redis": "ok"}


def test_health_reports_503_when_dependency_down(monkeypatch):
    def redis_down():
        raise ConnectionError("redis down")

    monkeypatch.setattr(main, "engine", FakeEngine(fail=True))
    monkeypatch.setattr(main, "get_redis_client", redis_down)

    response = TestClient(main.app).get("/health")

    assert response.status_code == 503
    assert response.json() == {"status": "error", "database": "error", "redis": "error"}
