"""gpa 自身设置：~/.config/gitpush/settings.toml。

管理 gpa 行为参数（排序方式、是否显示用法、颜色、默认动作），
并提供带注释的默认模板供用户自行配置。
"""
from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

from gitpush.utils import atomic_write

VALID_SORT_ORDERS = ("asc", "desc", "config")
VALID_ACTIONS = ("menu", "push")


@dataclass
class Settings:
    """gpa 行为设置。字段非法/缺失时回退默认值。"""

    sort_order: str = "asc"  # asc 字母序 | desc 倒序 | config 配置文件顺序
    show_usage: bool = True  # gpa 无参数时是否显示用法说明
    color: bool = True  # 是否启用 ANSI 颜色
    default_action: str = "menu"  # gpa 无参数时的默认动作: menu | push


def default_settings_path() -> Path:
    """设置文件默认路径：~/.config/gitpush/settings.toml。"""
    return Path.home() / ".config" / "gitpush" / "settings.toml"


SETTINGS_TEMPLATE = """\
# ==================== gpa 设置文件 ====================
# 本文件用于配置 gpa 自身的行为，以下列出全部可配置参数。
# 删除某一行即使用该参数的默认值；# 开头的行为注释。
# 修改保存后，下次运行 gpa 自动生效。

# 仓库显示/处理顺序:
#   asc    = 按名称字母序（默认）
#   desc   = 按名称字母倒序
#   config = 按配置文件中的书写顺序
sort_order = "asc"

# 执行 gpa（无参数）时是否显示用法说明（banner）
show_usage = true

# 是否启用 ANSI 颜色输出
color = true

# gpa 无参数时的默认动作:
#   menu = 进入交互菜单（默认）
#   push = 直接推送全部仓库
default_action = "menu"
"""


def load_settings(path: str | Path | None = None) -> Settings:
    """加载设置；文件不存在、格式错误或字段非法时使用默认值（宽松解析）。"""
    path = Path(path) if path else default_settings_path()
    settings = Settings()
    if not path.exists():
        return settings
    try:
        with open(path, "rb") as f:
            raw = tomllib.load(f)
    except (tomllib.TOMLDecodeError, OSError):
        return settings

    if raw.get("sort_order") in VALID_SORT_ORDERS:
        settings.sort_order = raw["sort_order"]
    if isinstance(raw.get("show_usage"), bool):
        settings.show_usage = raw["show_usage"]
    if isinstance(raw.get("color"), bool):
        settings.color = raw["color"]
    if raw.get("default_action") in VALID_ACTIONS:
        settings.default_action = raw["default_action"]
    return settings


def ensure_settings(path: str | Path | None = None) -> Path:
    """首次运行自动生成带注释的设置模板；已存在则跳过。返回设置文件路径。"""
    path = Path(path) if path else default_settings_path()
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write(path, SETTINGS_TEMPLATE)
    return path


def order_repos(repos: list, sort_order: str) -> list:
    """按 sort_order 对仓库列表排序（asc 升序 / desc 降序 / config 保持原序）。

    不区分大小写；返回新列表，不改动原配置。
    """
    if sort_order == "config":
        return list(repos)
    return sorted(
        repos,
        key=lambda r: r.name.lower(),
        reverse=(sort_order == "desc"),
    )
