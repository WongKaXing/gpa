"""状态管理: 保存和加载上次使用的配置文件路径。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from gitpush.utils import atomic_write


def os_default_state_dir() -> Path:
    """按操作系统返回默认状态目录。"""
    if sys.platform == "darwin":
        return Path.home() / ".config" / "gitpush"
    if sys.platform == "win32":
        return Path.home() / "AppData" / "Local" / "gitpush"
    return Path.home() / ".config" / "gitpush"


def _state_dir() -> Path:
    """返回状态文件目录，确保目录存在。"""
    base = os_default_state_dir()
    base.mkdir(parents=True, exist_ok=True)
    return base


def state_file_path() -> Path:
    return _state_dir() / "state.json"


def save_config_path(config_path: str | Path) -> None:
    """保存配置文件路径到状态文件。"""
    atomic_write(
        state_file_path(),
        json.dumps({"config_path": str(Path(config_path).resolve())}, indent=2)
    )


def load_config_path() -> str | None:
    """加载上次保存的配置文件路径，若不存在或无效返回 None。"""
    sf = state_file_path()
    if not sf.exists():
        return None
    try:
        data = json.loads(sf.read_text())
        path = data.get("config_path")
        if isinstance(path, str) and path:
            return path
        return None
    except (json.JSONDecodeError, KeyError):
        return None
