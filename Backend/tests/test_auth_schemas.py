# -*- coding: utf-8 -*-

import os
import sys

import pytest
from pydantic import ValidationError

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from auth.schemas import ChangePasswordRequest, UpdateProfileRequest, UserCreate


def test_user_create_accepts_strong_password():
    user = UserCreate(
        username="ali_kaya",
        email="ali@example.com",
        password="Gizli123",
    )
    assert user.username == "ali_kaya"


@pytest.mark.parametrize(
    "password",
    ["abcdefgh", "ABCDEFGH1", "abcdefg1", "Abcdefgh"],
)
def test_user_create_rejects_weak_password(password: str):
    with pytest.raises(ValidationError):
        UserCreate(username="ali_kaya", email="ali@example.com", password=password)


@pytest.mark.parametrize(
    "username",
    ["ab", "admin;drop", "user name", "root<script>"],
)
def test_user_create_rejects_invalid_username(username: str):
    with pytest.raises(ValidationError):
        UserCreate(username=username, email="ali@example.com", password="Gizli123")


def test_change_password_rejects_weak_new_password():
    with pytest.raises(ValidationError):
        ChangePasswordRequest(current_password="Oldpass1", new_password="weak")


def test_update_profile_rejects_invalid_username():
    with pytest.raises(ValidationError):
        UpdateProfileRequest(username="bad name")
