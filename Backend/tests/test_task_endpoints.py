# -*- coding: utf-8 -*-
"""Task endpoint tests for the canonical task contract."""

import os
import sys

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from api import endpoints  # noqa: E402
from core.task_status import TaskStatusStore  # noqa: E402


class FakeRedis:
    def __init__(self):
        self.data = {}

    def ping(self):
        return True

    def get(self, key):
        return self.data.get(key)

    def setex(self, key, ttl, value):
        self.data[key] = value

    def scan_iter(self, pattern):
        prefix = pattern.rstrip("*")
        for key in list(self.data.keys()):
            if key.startswith(prefix):
                yield key


class DummyTaskCallable:
    def __init__(self):
        self.calls = []

    def apply_async(self, **kwargs):
        self.calls.append(kwargs)


def create_test_client(monkeypatch):
    app = FastAPI()
    app.include_router(endpoints.router, prefix="/api/v1")
    store = TaskStatusStore(redis_client=FakeRedis())
    monkeypatch.setattr(endpoints, "get_task_status_store", lambda: store)
    return TestClient(app), store


def test_scrape_start_returns_queued_status(monkeypatch):
    client, store = create_test_client(monkeypatch)
    dummy_task = DummyTaskCallable()
    monkeypatch.setattr(endpoints, "scrape_emlakjet_task", dummy_task)

    response = client.post(
        "/api/v1/scrape/emlakjet",
        json={
            "listing_type": "satilik",
            "category": "konut",
            "scraping_method": "selenium",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "queued"
    assert payload["task_id"]
    stored = store.get_task(payload["task_id"])
    assert stored["status"] == "queued"
    assert dummy_task.calls[0]["task_id"] == payload["task_id"]


def test_get_task_status_returns_canonical_payload(monkeypatch):
    client, store = create_test_client(monkeypatch)
    store.create_queued_task("task-1", message="Queued", platform="hepsiemlak")
    store.mark_running("task-1", message="Running")

    response = client.get("/api/v1/tasks/task-1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["task_id"] == "task-1"
    assert payload["status"] == "running"
    assert "is_running" not in payload


def test_get_task_status_returns_404_when_missing(monkeypatch):
    client, _ = create_test_client(monkeypatch)

    response = client.get("/api/v1/tasks/missing-task")

    assert response.status_code == 404
    assert response.json()["detail"] == "Task not found"


def test_get_active_tasks_only_returns_active_statuses(monkeypatch):
    client, store = create_test_client(monkeypatch)
    store.create_queued_task("task-1", message="Queued", platform="emlakjet")
    store.mark_running("task-2", message="Running", platform="hepsiemlak")
    store.mark_completed("task-3", message="Done")

    response = client.get("/api/v1/tasks/active")

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 2
    assert {item["task_id"] for item in payload["active_tasks"]} == {"task-1", "task-2"}
