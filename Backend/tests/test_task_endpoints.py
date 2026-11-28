"""Task endpoint tests for the canonical task contract."""

import os
import sys
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from api import endpoints
from auth.dependencies import get_current_user
from core.task_status import TaskStatusStore

from tests.fake_task_redis import FakeRedis


class DummyTaskCallable:
    def __init__(self):
        self.calls = []

    def apply_async(self, **kwargs):
        self.calls.append(kwargs)


class FailingTaskCallable:
    def apply_async(self, **kwargs):
        raise ConnectionError("broker down")


USER = SimpleNamespace(id=1, is_admin=False)
OTHER_USER = SimpleNamespace(id=2, is_admin=False)
ADMIN = SimpleNamespace(id=99, is_admin=True)


def create_test_client(monkeypatch, authenticated=True, user=USER):
    app = FastAPI()
    app.include_router(endpoints.router, prefix="/api/v1")
    if authenticated:
        app.dependency_overrides[get_current_user] = lambda: user
    store = TaskStatusStore(redis_client=FakeRedis())
    monkeypatch.setattr(endpoints, "get_task_status_store", lambda: store)
    return TestClient(app), store


def test_scrape_requires_auth(monkeypatch):
    client, _store = create_test_client(monkeypatch, authenticated=False)

    response = client.post(
        "/api/v1/scrape/emlakjet",
        json={
            "listing_type": "satilik",
            "category": "konut",
            "scraping_method": "selenium",
        },
    )

    assert response.status_code == 401


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
    assert stored["user_id"] == USER.id
    assert dummy_task.calls[0]["task_id"] == payload["task_id"]


def test_scrape_enqueue_failure_marks_task_failed(monkeypatch):
    client, store = create_test_client(monkeypatch)
    monkeypatch.setattr(endpoints, "scrape_emlakjet_task", FailingTaskCallable())

    response = client.post(
        "/api/v1/scrape/emlakjet",
        json={
            "listing_type": "satilik",
            "category": "konut",
            "scraping_method": "selenium",
        },
    )

    assert response.status_code == 503
    (stored,) = [
        store.get_task(key.removeprefix("scrape_task:"))
        for key in store.redis_client.data
        if key.startswith("scrape_task:")
    ]
    assert stored["status"] == "failed"
    assert store.get_active_tasks() == []


def test_task_endpoints_hide_other_users_tasks(monkeypatch):
    client, store = create_test_client(monkeypatch, user=OTHER_USER)
    store.create_queued_task("task-1", message="Queued", user_id=USER.id)

    assert client.get("/api/v1/tasks/task-1").status_code == 404
    assert client.post("/api/v1/tasks/task-1/cancel").status_code == 404
    assert client.get("/api/v1/tasks/active").json()["count"] == 0
    assert store.get_task("task-1")["status"] == "queued"


def test_admin_sees_all_tasks(monkeypatch):
    client, store = create_test_client(monkeypatch, user=ADMIN)
    store.create_queued_task("task-1", message="Queued", user_id=USER.id)

    assert client.get("/api/v1/tasks/task-1").status_code == 200
    assert client.get("/api/v1/tasks/active").json()["count"] == 1


def test_get_task_status_returns_canonical_payload(monkeypatch):
    client, store = create_test_client(monkeypatch)
    store.create_queued_task(
        "task-1", message="Queued", platform="hepsiemlak", user_id=USER.id
    )
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
    store.create_queued_task(
        "task-1", message="Queued", platform="emlakjet", user_id=USER.id
    )
    store.create_queued_task("task-2", message="Queued", user_id=USER.id)
    store.mark_running("task-2", message="Running", platform="hepsiemlak")
    store.create_queued_task("task-3", message="Queued", user_id=USER.id)
    store.mark_completed("task-3", message="Done")

    response = client.get("/api/v1/tasks/active")

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 2
    assert {item["task_id"] for item in payload["active_tasks"]} == {"task-1", "task-2"}


def test_cancel_task_marks_cancelled(monkeypatch):
    client, store = create_test_client(monkeypatch)
    store.create_queued_task(
        "task-1", message="Queued", platform="emlakjet", user_id=USER.id
    )
    store.mark_running("task-1", message="Running")

    revoked = []
    monkeypatch.setattr(
        endpoints.celery_app.control,
        "revoke",
        lambda task_id, terminate=False: revoked.append((task_id, terminate)),
    )

    response = client.post("/api/v1/tasks/task-1/cancel")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "cancelled"
    assert payload["task_id"] == "task-1"
    assert revoked == [("task-1", True)]


def test_cancel_task_rejects_finished_task(monkeypatch):
    client, store = create_test_client(monkeypatch)
    store.create_queued_task("task-1", message="Queued", user_id=USER.id)
    store.mark_completed("task-1", message="Done")

    response = client.post("/api/v1/tasks/task-1/cancel")

    assert response.status_code == 409
