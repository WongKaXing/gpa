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


@pytest.fixture(autouse=True)
def _isolate_state_file(tmp_path, monkeypatch):
    """隔离状态文件到临时目录，防止测试污染真实 ~/.config/gitpush/state.json。

    state.py 内部使用未 mock 的 Path.home()，若测试走 main()/save_config_path
    会把真实状态文件覆盖成临时路径，导致用户记住的配置丢失。
    """
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    monkeypatch.setattr(
        "gitpush.state.state_file_path",
        lambda: state_dir / "state.json",
    )


@pytest.fixture(autouse=True)
def _isolate_settings(tmp_path, monkeypatch):
    """隔离 gpa 设置文件，防止测试写真实 ~/.config/gitpush/settings.toml。"""
    settings_path = tmp_path / "settings.toml"
    monkeypatch.setattr(
        "gitpush.settings.default_settings_path",
        lambda: settings_path,
    )
    return settings_path
