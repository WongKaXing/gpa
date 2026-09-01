"""公共工具函数。"""
from __future__ import annotations

import os
import tempfile
import unicodedata
from pathlib import Path


def atomic_write(path: Path, content: str) -> None:
    """原子写入文件：先写临时文件，再重命名，避免中断导致文件损坏。"""
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(content)
        os.replace(tmp, path)
    except BaseException:
        os.unlink(tmp)
        raise


def display_width(text: str) -> int:
    """计算字符串的终端显示宽度（中文等宽字符计为 2）。"""
    w = 0
    for ch in text:
        ea = unicodedata.east_asian_width(ch)
        w += 2 if ea in ("W", "F") else 1
    return w


def pad_to(text: str, width: int) -> str:
    """将字符串填充到指定显示宽度（超出时不截断）。"""
    current = display_width(text)
    if current >= width:
        return text
    return text + " " * (width - current)


def center(text: str, width: int) -> str:
    """将字符串在指定显示宽度内居中对齐。"""
    pad = width - display_width(text)
    if pad <= 0:
        return text
    left = pad // 2
    return " " * left + text + " " * (pad - left)


_COLOR_ENABLED = True


def set_color_enabled(enabled: bool) -> None:
    """全局开关 ANSI 颜色（依据 gpa 设置文件 color 字段）。"""
    global _COLOR_ENABLED
    _COLOR_ENABLED = enabled


def color(text: str, code: str) -> str:
    """ANSI 着色：32 绿 / 31 红 / 33 黄 / 36 青 / 1 加粗。关闭时返回原文。"""
    if not _COLOR_ENABLED:
        return text
    return f"\033[{code}m{text}\033[0m"
