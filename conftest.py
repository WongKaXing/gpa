"""共享的 pytest fixture。"""
from __future__ import annotations

import pytest


@pytest.fixture
def fake_home(tmp_path, monkeypatch):
    """Mock Path.home() 返回一个临时目录（不含 .gitpush.toml）。"""
    home_dir = tmp_path / "home"
    home_dir.mkdir()
    monkeypatch.setattr("gitpush.cli.Path.home", lambda: home_dir)
    return home_dir
