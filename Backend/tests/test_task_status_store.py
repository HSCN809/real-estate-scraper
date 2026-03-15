# -*- coding: utf-8 -*-
"""Task status store tests."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.task_status import (  # noqa: E402
    TASK_STATUS_COMPLETED,
    TASK_STATUS_FAILED,
    TASK_STATUS_QUEUED,
    TASK_STATUS_RUNNING,
    TaskStatusStore,
    build_task_status_key,
    normalize_scrape_session_status,
)


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


def test_task_status_store_lifecycle():
    store = TaskStatusStore(redis_client=FakeRedis())

    queued = store.create_queued_task("task-1", message="Queued", platform="hepsiemlak")
    assert queued["status"] == TASK_STATUS_QUEUED
    assert queued["platform"] == "hepsiemlak"
    assert queued["finished_at"] is None

    running = store.mark_running("task-1", message="Running", platform="hepsiemlak", progress=10)
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
