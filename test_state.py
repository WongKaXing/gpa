"""Tests for state management module."""
import json
import tempfile
from pathlib import Path
from unittest import mock

from gitpush.state import (
    save_config_path,
    load_config_path,
    os_default_state_dir,
    state_file_path,
)


def test_os_default_state_dir_is_absolute():
    d = os_default_state_dir()
    assert d.is_absolute()
    assert d.name == "gitpush"


def test_save_and_load_config_path():
    with tempfile.TemporaryDirectory() as tmp:
        # 用临时目录覆盖状态目录
        state_file = Path(tmp) / "state.json"
        with mock.patch("gitpush.state.state_file_path", return_value=state_file):
            save_config_path("/tmp/my-gitpush.toml")
            assert state_file.exists()

            loaded = load_config_path()
            assert loaded == str(Path("/tmp/my-gitpush.toml").resolve())


def test_load_config_path_nonexistent():
    with tempfile.TemporaryDirectory() as tmp:
        state_file = Path(tmp) / "nonexistent.json"
        with mock.patch("gitpush.state.state_file_path", return_value=state_file):
            assert load_config_path() is None


def test_load_config_path_corrupted():
    with tempfile.TemporaryDirectory() as tmp:
        state_file = Path(tmp) / "state.json"
        state_file.write_text("not json")
        with mock.patch("gitpush.state.state_file_path", return_value=state_file):
            assert load_config_path() is None


def test_save_overwrites_previous():
    with tempfile.TemporaryDirectory() as tmp:
        state_file = Path(tmp) / "state.json"
        with mock.patch("gitpush.state.state_file_path", return_value=state_file):
            save_config_path("/first.toml")
            save_config_path("/second.toml")
            loaded = load_config_path()
            assert loaded == str(Path("/second.toml").resolve())
