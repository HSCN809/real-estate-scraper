"""Chrome cleanup must only target this process's own descendants."""

import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core import driver_manager


def test_kill_zombie_chrome_scopes_pkill_to_own_tree(monkeypatch):
    me = str(os.getpid())
    children = {me: "100 101", "100": "200", "101": "", "200": ""}
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        if cmd[0] == "pgrep":
            return SimpleNamespace(stdout=children[cmd[2]])
        return SimpleNamespace(stdout="")

    monkeypatch.setattr(driver_manager.subprocess, "run", fake_run)
    monkeypatch.setattr(driver_manager.time, "sleep", lambda _: None)

    driver_manager._kill_zombie_chrome()

    pkill = [cmd for cmd in calls if cmd[0] == "pkill"]
    assert len(pkill) == 1
    assert pkill[0][:4] == ["pkill", "-f", "chrome", "-P"]
    assert set(pkill[0][4].split(",")) == {me, "100", "101", "200"}
