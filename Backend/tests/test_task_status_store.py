"""Task status store tests."""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.task_status import (
    ACTIVE_TASKS_KEY,
    TASK_STATUS_CANCELLED,
    TASK_STATUS_COMPLETED,
    TASK_STATUS_FAILED,
    TASK_STATUS_QUEUED,
    TASK_STATUS_RUNNING,
    TaskStatusStore,
    build_task_status_key,
    create_task_status_payload,
    normalize_scrape_session_status,
)

from tests.fake_task_redis import FakeRedis


def test_task_status_store_lifecycle():
    store = TaskStatusStore(redis_client=FakeRedis())

    queued = store.create_queued_task("task-1", message="Queued", platform="hepsiemlak")
    assert queued["status"] == TASK_STATUS_QUEUED
    assert queued["platform"] == "hepsiemlak"
    assert queued["finished_at"] is None

    running = store.mark_running(
        "task-1", message="Running", platform="hepsiemlak", progress=10
    )
    assert running["status"] == TASK_STATUS_RUNNING
    assert running["progress"] == 10
    assert running["finished_at"] is None

    completed = store.mark_completed("task-1", message="Done")
    assert completed["status"] == TASK_STATUS_COMPLETED
    assert completed["progress"] == 100
    assert completed["finished_at"] is not None


def test_task_status_store_filters_active_tasks():
    store = TaskStatusStore(redis_client=FakeRedis())
    store.create_queued_task("task-1", message="Queued", platform="emlakjet")
    store.mark_running("task-2", message="Running", platform="hepsiemlak")
    store.mark_failed("task-3", message="Failed", error="boom")

    active_ids = [item["task_id"] for item in store.get_active_tasks()]
    assert set(active_ids) == {"task-1", "task-2"}


def test_build_task_status_key_and_normalize_legacy_statuses():
    assert build_task_status_key("abc") == "scrape_task:abc"
    assert normalize_scrape_session_status("timeout") == TASK_STATUS_FAILED
    assert normalize_scrape_session_status("terminated") == TASK_STATUS_FAILED
    assert normalize_scrape_session_status("cancelled") == TASK_STATUS_FAILED


def test_active_index_migrates_legacy_tasks_and_keeps_order():
    client = FakeRedis()
    store = TaskStatusStore(redis_client=client)
    legacy_key = build_task_status_key("legacy")
    client.data[legacy_key] = json.dumps(
        create_task_status_payload(
            "legacy",
            status=TASK_STATUS_RUNNING,
            message="Old",
            updated_at="2025-01-01T00:00:00+00:00",
        )
    )
    store.create_queued_task("new", message="New")
    store.mark_completed("done", message="Done")

    assert [task["task_id"] for task in store.get_active_tasks()] == ["new", "legacy"]
    assert legacy_key in client.smembers(ACTIVE_TASKS_KEY)
    assert build_task_status_key("done") not in client.smembers(ACTIVE_TASKS_KEY)

    store.mark_cancelled("legacy")
    store.mark_failed("new", message="Failed")
    assert legacy_key not in client.smembers(ACTIVE_TASKS_KEY)
    assert build_task_status_key("new") not in client.smembers(ACTIVE_TASKS_KEY)
    assert store.get_active_tasks() == []
    assert client.scan_calls == 1


def test_active_index_removes_expired_status(monkeypatch):
    client = FakeRedis()
    store = TaskStatusStore(redis_client=client)
    store.create_queued_task("expired", message="Queued")
    store.create_queued_task("restarted", message="Queued")
    assert len(store.get_active_tasks()) == 2

    expired_key = build_task_status_key("expired")
    restarted_key = build_task_status_key("restarted")
    del client.data[expired_key]
    del client.data[restarted_key]
    original_mget = client.mget

    def mget(keys):
        snapshot = original_mget(keys)
        store.mark_running("restarted", message="Restarted")
        return snapshot

    monkeypatch.setattr(client, "mget", mget)
    assert store.get_active_tasks() == []
    assert expired_key not in client.smembers(ACTIVE_TASKS_KEY)
    assert restarted_key in client.smembers(ACTIVE_TASKS_KEY)
    monkeypatch.setattr(client, "mget", original_mget)
    assert [task["task_id"] for task in store.get_active_tasks()] == ["restarted"]
    assert client.scan_calls == 1


def test_progress_does_not_move_backwards():
    store = TaskStatusStore(redis_client=FakeRedis())
    store.create_queued_task("task-1", message="Queued")
    store.mark_running("task-1", message="Running", progress=80)
    updated = store.update("task-1", progress=10, message="Retry")
    assert updated["progress"] == 80
    assert updated["message"] == "Retry"


def test_final_status_ignores_later_updates():
    store = TaskStatusStore(redis_client=FakeRedis())
    store.create_queued_task("task-1", message="Queued")
    store.mark_cancelled("task-1")
    updated = store.update(
        "task-1", status=TASK_STATUS_RUNNING, message="Still going", progress=40
    )
    assert updated["status"] == TASK_STATUS_CANCELLED
    assert store.is_cancel_requested("task-1")


def test_append_log_keeps_recent_events():
    store = TaskStatusStore(redis_client=FakeRedis())
    store.create_queued_task("task-1", message="Queued")
    store.mark_running("task-1", message="Running")
    store.append_log("task-1", "Şırnak atlandı (0 ilan)", "warning")
    store.append_log("task-1", "Şırnak atlandı (0 ilan)", "warning")
    store.append_log("task-1", "Cizre ilçesi alınamadı", "error")
    task = store.get_task("task-1")
    assert [item["text"] for item in task["logs"]] == [
        "Şırnak atlandı (0 ilan)",
        "Cizre ilçesi alınamadı",
    ]


def test_single_roundtrip_update_logs_and_checks_cancellation():
    import pytest
    from core.task_status import TaskCancelled

    client = FakeRedis()
    store = TaskStatusStore(redis_client=client)
    store.create_queued_task("task-1", message="Queued", platform="hepsiemlak")

    updated = store.update(
        "task-1",
        status=TASK_STATUS_RUNNING,
        message="İstanbul - Sayfa 1/5",
        progress=20,
        log_message="İstanbul - Sayfa 1/5",
        check_cancel=True,
    )
    assert updated["progress"] == 20
    assert [item["text"] for item in updated["logs"]] == ["İstanbul - Sayfa 1/5"]

    store.mark_cancelled("task-1")
    with pytest.raises(TaskCancelled):
        store.update(
            "task-1",
            message="İstanbul - Sayfa 2/5",
            progress=40,
            log_message="İstanbul - Sayfa 2/5",
            check_cancel=True,
        )


def test_update_retries_on_watch_conflict_and_preserves_cancellation(monkeypatch):
    import pytest
    import redis as redis_lib
    from core.task_status import TaskCancelled

    client = FakeRedis()
    store = TaskStatusStore(redis_client=client)
    store.create_queued_task("task-1", message="Queued", platform="hepsiemlak")
    store.mark_running("task-1", message="Running", progress=10)

    orig_pipeline = client.pipeline
    conflicts = [0]

    def racing_pipeline():
        pipe = orig_pipeline()
        orig_execute = pipe.execute

        def execute():
            if conflicts[0] == 0:
                conflicts[0] += 1
                TaskStatusStore(redis_client=client).mark_cancelled("task-1")
                raise redis_lib.WatchError("concurrent cancel")
            return orig_execute()

        pipe.execute = execute
        return pipe

    monkeypatch.setattr(client, "pipeline", racing_pipeline)
    with pytest.raises(TaskCancelled):
        store.update("task-1", progress=50, check_cancel=True)
    assert conflicts[0] == 1
    assert store.get_task("task-1")["status"] == TASK_STATUS_CANCELLED
