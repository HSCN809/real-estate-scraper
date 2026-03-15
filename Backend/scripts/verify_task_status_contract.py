# -*- coding: utf-8 -*-
"""Validate the canonical Redis/API task status contract."""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict

import requests
from celery.result import AsyncResult

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from celery_app import celery_app  # noqa: E402
from core.task_status import (  # noqa: E402
    TASK_STATUS_KEY_PREFIX,
    TASK_STATUS_VALUES,
    get_redis_client,
)


def validate_payload(payload: Dict[str, Any]) -> None:
    required = {
        "task_id",
        "status",
        "message",
        "progress",
        "current",
        "total",
        "details",
        "error",
        "platform",
        "started_at",
        "updated_at",
        "finished_at",
    }
    missing = required - payload.keys()
    if missing:
        raise SystemExit(f"Missing payload keys: {sorted(missing)}")
    if payload["status"] not in TASK_STATUS_VALUES:
        raise SystemExit(f"Unsupported task status: {payload['status']}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-base", default=os.getenv("VERIFY_API_BASE", "http://localhost:8000/api/v1"))
    parser.add_argument("--task-id", help="Validate a specific task id as well")
    args = parser.parse_args()

    redis_client = get_redis_client()
    keys = list(redis_client.scan_iter(f"{TASK_STATUS_KEY_PREFIX}:*"))
    print(f"Redis task keys: {len(keys)}")
    for key in keys[:10]:
        payload = json.loads(redis_client.get(key))
        validate_payload(payload)
        print(f"- {key}: {payload['status']} ({payload['message']})")

    if not args.task_id:
        return 0

    redis_payload = json.loads(redis_client.get(f"{TASK_STATUS_KEY_PREFIX}:{args.task_id}"))
    validate_payload(redis_payload)

    response = requests.get(f"{args.api_base}/tasks/{args.task_id}", timeout=10)
    response.raise_for_status()
    api_payload = response.json()
    validate_payload(api_payload)

    celery_result = AsyncResult(args.task_id, app=celery_app)
    print("\nTask comparison")
    print(f"Redis/API status: {redis_payload['status']}")
    print(f"Celery backend status: {celery_result.status}")
    print("API payload validated successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
