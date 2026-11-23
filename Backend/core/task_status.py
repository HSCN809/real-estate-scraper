from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime
from functools import lru_cache
from typing import Any, cast

import redis

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://real-estate-redis:6379/0")
TASK_STATUS_KEY_PREFIX = "scrape_task"
TASK_STATUS_TTL_SECONDS = 86400
ACTIVE_TASKS_KEY = "scrape_active_tasks"
ACTIVE_TASKS_INDEX_READY_KEY = "scrape_active_tasks:indexed"

TASK_STATUS_QUEUED = "queued"
TASK_STATUS_RUNNING = "running"
TASK_STATUS_COMPLETED = "completed"
TASK_STATUS_FAILED = "failed"
TASK_STATUS_CANCELLED = "cancelled"

ACTIVE_TASK_STATUSES = {TASK_STATUS_QUEUED, TASK_STATUS_RUNNING}
FINAL_TASK_STATUSES = {
    TASK_STATUS_COMPLETED,
    TASK_STATUS_FAILED,
    TASK_STATUS_CANCELLED,
}
TASK_STATUS_VALUES = ACTIVE_TASK_STATUSES | FINAL_TASK_STATUSES

SCRAPE_SESSION_STATUS_RUNNING = "running"
SCRAPE_SESSION_STATUS_COMPLETED = "completed"
SCRAPE_SESSION_STATUS_FAILED = "failed"
SCRAPE_SESSION_STATUS_VALUES = {
    SCRAPE_SESSION_STATUS_RUNNING,
    SCRAPE_SESSION_STATUS_COMPLETED,
    SCRAPE_SESSION_STATUS_FAILED,
}
LEGACY_SCRAPE_SESSION_STATUS_MAP = {
    "timeout": SCRAPE_SESSION_STATUS_FAILED,
    "terminated": SCRAPE_SESSION_STATUS_FAILED,
    "stopped": SCRAPE_SESSION_STATUS_FAILED,
    "cancelled": SCRAPE_SESSION_STATUS_FAILED,
}


class TaskCancelled(Exception):
    pass


def utcnow_iso() -> str:
    return datetime.now(UTC).isoformat()


def build_task_status_key(task_id: str) -> str:
    return f"{TASK_STATUS_KEY_PREFIX}:{task_id}"


def is_active_task_status(status: str | None) -> bool:
    return status in ACTIVE_TASK_STATUSES


def is_final_task_status(status: str | None) -> bool:
    return status in FINAL_TASK_STATUSES


def normalize_scrape_session_status(status: str) -> str:
    return LEGACY_SCRAPE_SESSION_STATUS_MAP.get(status, status)


def create_task_status_payload(
    task_id: str,
    *,
    status: str,
    message: str,
    progress: int = 0,
    current: int = 0,
    total: int = 0,
    details: str = "",
    error: str | None = None,
    platform: str | None = None,
    started_at: str | None = None,
    updated_at: str | None = None,
    finished_at: str | None = None,
    unit: str = "",
    cancel_requested: bool = False,
    logs: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    if status not in TASK_STATUS_VALUES:
        raise ValueError(f"Unsupported task status: {status}")

    now = utcnow_iso()
    payload = {
        "task_id": task_id,
        "status": status,
        "message": message,
        "progress": progress,
        "current": current,
        "total": total,
        "details": details,
        "error": error,
        "platform": platform,
        "started_at": started_at or now,
        "updated_at": updated_at or now,
        "finished_at": finished_at,
        "unit": unit,
        "cancel_requested": cancel_requested,
        "logs": list(logs or []),
    }
    if is_final_task_status(status) and payload["finished_at"] is None:
        payload["finished_at"] = payload["updated_at"]
    return payload


@lru_cache(maxsize=1)
def get_redis_client() -> redis.Redis:
    client = redis.from_url(REDIS_URL, decode_responses=True)
    client.ping()
    return client


class TaskStatusStore:
    def __init__(self, redis_client: redis.Redis | None = None):
        self.redis_client = redis_client or get_redis_client()

    def create_queued_task(
        self, task_id: str, *, message: str, platform: str | None = None
    ) -> dict[str, Any]:
        payload = create_task_status_payload(
            task_id,
            status=TASK_STATUS_QUEUED,
            message=message,
            platform=platform,
        )
        self._write(payload)
        return payload

    def update(
        self,
        task_id: str,
        *,
        status: str | None = None,
        message: str | None = None,
        progress: int | None = None,
        current: int | None = None,
        total: int | None = None,
        details: str | None = None,
        error: str | None = None,
        platform: str | None = None,
        unit: str | None = None,
        cancel_requested: bool | None = None,
    ) -> dict[str, Any]:
        existing = self.get_task(task_id)
        if existing is None:
            if status is None:
                raise ValueError(
                    "status is required when creating a missing task payload"
                )
            existing = create_task_status_payload(
                task_id,
                status=status,
                message=message or "",
                platform=platform,
            )
        elif is_final_task_status(existing.get("status")):
            return existing

        if status is not None:
            if status not in TASK_STATUS_VALUES:
                raise ValueError(f"Unsupported task status: {status}")
            existing["status"] = status
        if message is not None:
            existing["message"] = message
        if progress is not None:
            previous = int(existing.get("progress") or 0)
            if (
                existing.get("status") in ACTIVE_TASK_STATUSES
                and progress < previous
            ):
                progress = previous
            existing["progress"] = progress
        if current is not None:
            existing["current"] = current
        if total is not None:
            existing["total"] = total
        if details is not None:
            existing["details"] = details
        if error is not None:
            existing["error"] = error
        if platform is not None:
            existing["platform"] = platform
        if unit is not None:
            existing["unit"] = unit
        if cancel_requested is not None:
            existing["cancel_requested"] = cancel_requested
        existing.setdefault("logs", [])

        existing["updated_at"] = utcnow_iso()
        if is_final_task_status(existing["status"]):
            existing["finished_at"] = existing["updated_at"]
        else:
            existing["finished_at"] = None

        self._write(existing)
        return existing

    def mark_running(
        self,
        task_id: str,
        *,
        message: str,
        platform: str | None = None,
        progress: int = 0,
    ) -> dict[str, Any]:
        return self.update(
            task_id,
            status=TASK_STATUS_RUNNING,
            message=message,
            progress=progress,
            platform=platform,
        )

    def mark_completed(
        self,
        task_id: str,
        *,
        message: str,
        details: str = "",
    ) -> dict[str, Any]:
        return self.update(
            task_id,
            status=TASK_STATUS_COMPLETED,
            message=message,
            progress=100,
            details=details,
            error=None,
        )

    def mark_failed(
        self,
        task_id: str,
        *,
        message: str,
        error: str | None = None,
        details: str = "",
    ) -> dict[str, Any]:
        return self.update(
            task_id,
            status=TASK_STATUS_FAILED,
            message=message,
            error=error,
            details=details,
        )

    def mark_cancelled(
        self,
        task_id: str,
        *,
        message: str = "Tarama iptal edildi.",
    ) -> dict[str, Any]:
        payload = self.update(
            task_id,
            status=TASK_STATUS_CANCELLED,
            message=message,
            details="Kullanıcı tarafından durduruldu",
            cancel_requested=True,
        )
        self.append_log(task_id, message, "warning")
        return payload

    def is_cancel_requested(self, task_id: str) -> bool:
        task = self.get_task(task_id)
        if task is None:
            return False
        return bool(
            task.get("cancel_requested")
            or task.get("status") == TASK_STATUS_CANCELLED
        )

    def append_log(
        self,
        task_id: str,
        message: str,
        level: str = "info",
    ) -> dict[str, Any] | None:
        existing = self.get_task(task_id)
        if existing is None:
            return None
        text = " ".join(str(message or "").split())
        if not text:
            return existing
        logs = list(existing.get("logs") or [])
        if logs and logs[-1].get("text") == text:
            return existing
        logs.append({"text": text, "level": level})
        existing["logs"] = logs[-40:]
        existing["updated_at"] = utcnow_iso()
        self._write(existing)
        return existing

    def get_task(self, task_id: str) -> dict[str, Any] | None:
        data = self.redis_client.get(build_task_status_key(task_id))
        if not data:
            return None
        return json.loads(cast(str | bytes, data))

    def get_active_tasks(self) -> list[dict[str, Any]]:
        if not self.redis_client.exists(ACTIVE_TASKS_INDEX_READY_KEY):
            self._index_existing_active_tasks()

        keys = list(
            cast(set[str | bytes], self.redis_client.smembers(ACTIVE_TASKS_KEY))
        )
        if not keys:
            return []

        tasks: list[dict[str, Any]] = []
        values = cast(list[str | bytes | None], self.redis_client.mget(keys))
        for key, data in zip(keys, values, strict=True):
            if data is None:
                self._sync_active_member(key, None)
                continue
            if data:
                payload = json.loads(data)
                if is_active_task_status(payload.get("status")):
                    tasks.append(payload)
        tasks.sort(key=lambda item: item.get("updated_at") or "", reverse=True)
        return tasks

    def _index_existing_active_tasks(self) -> None:
        for key in self.redis_client.scan_iter(f"{TASK_STATUS_KEY_PREFIX}:*"):
            data = cast(str | bytes | None, self.redis_client.get(key))
            if data and is_active_task_status(json.loads(data).get("status")):
                self._sync_active_member(key, data)
        self.redis_client.set(ACTIVE_TASKS_INDEX_READY_KEY, "1")

    def _sync_active_member(
        self, key: str | bytes, expected: str | bytes | None
    ) -> None:
        # Migration and expiry cleanup can race with a worker writing this task.
        with self.redis_client.pipeline() as pipe:
            while True:
                try:
                    pipe.watch(key)
                    if pipe.get(key) != expected:
                        return
                    pipe.multi()
                    if expected is None:
                        pipe.srem(ACTIVE_TASKS_KEY, key)
                    else:
                        pipe.sadd(ACTIVE_TASKS_KEY, key)
                    pipe.execute()
                    return
                except redis.WatchError:
                    continue

    def _write(self, payload: dict[str, Any]) -> None:
        key = build_task_status_key(payload["task_id"])
        with self.redis_client.pipeline() as pipe:
            pipe.setex(key, TASK_STATUS_TTL_SECONDS, json.dumps(payload))
            if is_active_task_status(payload["status"]):
                pipe.sadd(ACTIVE_TASKS_KEY, key)
            else:
                pipe.srem(ACTIVE_TASKS_KEY, key)
            pipe.execute()


def get_task_status_store() -> TaskStatusStore:
    return TaskStatusStore()
