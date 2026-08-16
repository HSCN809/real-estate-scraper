# -*- coding: utf-8 -*-

import os
import uuid

import pytest
import requests

API = os.getenv("SMOKE_API_URL", "http://127.0.0.1:8000")


def _api_up() -> bool:
    try:
        return requests.get(f"{API}/", timeout=3).status_code == 200
    except requests.RequestException:
        return False


pytestmark = pytest.mark.skipif(not _api_up(), reason="API not running")


def test_api_root_health():
    response = requests.get(f"{API}/", timeout=5)
    assert response.status_code == 200
    assert "running" in response.json()["message"].lower()


def test_register_and_login_roundtrip():
    suffix = uuid.uuid4().hex[:8]
    payload = {
        "username": f"smoke_{suffix}",
        "email": f"smoke_{suffix}@example.com",
        "password": "SmokeTest1",
    }
    created = requests.post(f"{API}/api/v1/auth/register", json=payload, timeout=10)
    assert created.status_code == 201, created.text
    assert created.json()["username"] == payload["username"]

    login = requests.post(
        f"{API}/api/v1/auth/login",
        json={"username": payload["username"], "password": payload["password"]},
        timeout=10,
    )
    assert login.status_code == 200, login.text
    assert login.json()["username"] == payload["username"]
