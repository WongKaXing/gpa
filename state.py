"""状态管理: 保存和加载上次使用的配置文件路径。"""
from __future__ import annotations

import json
from pathlib import Path


def _state_dir() -> Path:
    """返回状态文件目录，确保目录存在。"""
    base = os_default_state_dir()
    base.mkdir(parents=True, exist_ok=True)
    return base


def os_default_state_dir() -> Path:
    """按操作系统返回默认状态目录。"""
    import sys
    if sys.platform == "darwin":
        return Path.home() / ".config" / "gitpush"
    if sys.platform == "win32":
        return Path.home() / "AppData" / "Local" / "gitpush"
    xdg = Path.home() / ".config" / "gitpush"
    return xdg


def state_file_path() -> Path:
    return _state_dir() / "state.json"


def save_config_path(config_path: str | Path) -> None:
    """保存配置文件路径到状态文件。"""
    state_file_path().write_text(
        json.dumps({"config_path": str(Path(config_path).resolve())}, indent=2)
    )


def load_config_path() -> str | None:
    """加载上次保存的配置文件路径，若不存在返回 None。"""
    sf = state_file_path()
    if not sf.exists():
        return None
    try:
        data = json.loads(sf.read_text())
        return data.get("config_path")
    except (json.JSONDecodeError, KeyError):
        return None
