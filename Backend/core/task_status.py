from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from functools import lru_cache
from typing import Any, Dict, List, Optional

import redis

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://real-estate-redis:6379/0")
TASK_STATUS_KEY_PREFIX = "scrape_task"
TASK_STATUS_TTL_SECONDS = 86400

TASK_STATUS_QUEUED = "queued"
TASK_STATUS_RUNNING = "running"
TASK_STATUS_COMPLETED = "completed"
TASK_STATUS_FAILED = "failed"

ACTIVE_TASK_STATUSES = {TASK_STATUS_QUEUED, TASK_STATUS_RUNNING}
FINAL_TASK_STATUSES = {TASK_STATUS_COMPLETED, TASK_STATUS_FAILED}
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
}


def utcnow_iso() -> str:
    return datetime.utcnow().isoformat()


def build_task_status_key(task_id: str) -> str:
    return f"{TASK_STATUS_KEY_PREFIX}:{task_id}"


def is_active_task_status(status: Optional[str]) -> bool:
    return status in ACTIVE_TASK_STATUSES


def is_final_task_status(status: Optional[str]) -> bool:
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
    error: Optional[str] = None,
    platform: Optional[str] = None,
    started_at: Optional[str] = None,
    updated_at: Optional[str] = None,
    finished_at: Optional[str] = None,
) -> Dict[str, Any]:
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
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis_client = redis_client or get_redis_client()

    def create_queued_task(self, task_id: str, *, message: str, platform: Optional[str] = None) -> Dict[str, Any]:
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
        status: Optional[str] = None,
        message: Optional[str] = None,
        progress: Optional[int] = None,
        current: Optional[int] = None,
        total: Optional[int] = None,
        details: Optional[str] = None,
        error: Optional[str] = None,
        platform: Optional[str] = None,
    ) -> Dict[str, Any]:
        existing = self.get_task(task_id)
        if existing is None:
            if status is None:
                raise ValueError("status is required when creating a missing task payload")
            existing = create_task_status_payload(
                task_id,
                status=status,
                message=message or "",
                platform=platform,
            )

        if status is not None:
            if status not in TASK_STATUS_VALUES:
                raise ValueError(f"Unsupported task status: {status}")
            existing["status"] = status
        if message is not None:
            existing["message"] = message
        if progress is not None:
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
        platform: Optional[str] = None,
        progress: int = 0,
    ) -> Dict[str, Any]:
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
    ) -> Dict[str, Any]:
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
        error: Optional[str] = None,
        details: str = "",
    ) -> Dict[str, Any]:
        return self.update(
            task_id,
            status=TASK_STATUS_FAILED,
            message=message,
            error=error,
            details=details,
        )

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        data = self.redis_client.get(build_task_status_key(task_id))
        if not data:
            return None
        return json.loads(data)

    def get_active_tasks(self) -> List[Dict[str, Any]]:
        tasks: List[Dict[str, Any]] = []
        for key in self.redis_client.scan_iter(f"{TASK_STATUS_KEY_PREFIX}:*"):
            data = self.redis_client.get(key)
            if not data:
                continue
            payload = json.loads(data)
            if is_active_task_status(payload.get("status")):
                tasks.append(payload)
        tasks.sort(key=lambda item: item.get("updated_at") or "", reverse=True)
        return tasks

    def _write(self, payload: Dict[str, Any]) -> None:
        self.redis_client.setex(
            build_task_status_key(payload["task_id"]),
            TASK_STATUS_TTL_SECONDS,
            json.dumps(payload),
        )


def get_task_status_store() -> TaskStatusStore:
    return TaskStatusStore()
