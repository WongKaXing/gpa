"""File copy with glob-based exclusion."""
from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from fnmatch import fnmatch
from pathlib import Path

from gitpush.config import RepoConfig


@dataclass
class SyncResult:
    copied: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)


def _should_exclude(file_path: Path, exclude_patterns: list[str]) -> bool:
    name = file_path.name
    for pattern in exclude_patterns:
        if fnmatch(name, pattern) or fnmatch(str(file_path), pattern):
            return True
    return False


def _expand_path(raw: str, base_dir: Path) -> Path:
    p = Path(raw).expanduser()
    if not p.is_absolute():
        p = (base_dir / p).resolve()
    return p


def _copy_dir(src: Path, dst: Path, exclude: list[str], result: SyncResult) -> None:
    """递归复制 src 目录到 dst，跳过匹配 exclude 的文件。"""
    for item in src.rglob("*"):
        if not item.is_file():
            continue
        if _should_exclude(item, exclude):
            result.skipped.append(str(item))
            continue
        rel = item.relative_to(src)
        target = dst / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.unlink(missing_ok=True)
        shutil.copy2(item, target)
        result.copied.append(str(item))


def sync_files(repo: RepoConfig, config_dir: Path) -> SyncResult:
    """Copy source files/dirs into the repo, excluding matched patterns.

    支持两种同步来源（可并存）：
      1. sync_dir —— 同步整个目录到仓库根目录，配合 exclude 排除文件；
      2. files —— 逐条 source/dest 映射（旧语法）。

    Args:
        repo: RepoConfig with sync_dir/files, path, and exclude list.
        config_dir: Directory of the gitpush.toml, for resolving relative paths.

    Returns:
        SyncResult listing what was copied and what was skipped.
    """
    result = SyncResult()
    repo_path = _expand_path(repo.path, config_dir)
    exclude = repo.exclude or []

    if repo.sync_dir:
        src = _expand_path(repo.sync_dir, config_dir)
        if not src.exists():
            result.skipped.append(f"{repo.sync_dir} (未找到)")
        elif src.is_dir():
            _copy_dir(src, repo_path, exclude, result)
        else:
            if _should_exclude(src, exclude):
                result.skipped.append(f"{repo.sync_dir} (已排除)")
            else:
                repo_path.mkdir(parents=True, exist_ok=True)
                target = repo_path / src.name
                target.unlink(missing_ok=True)
                shutil.copy2(src, target)
                result.copied.append(str(src))

    for entry in repo.files:
        src = _expand_path(entry.source, config_dir)
        dst = repo_path / entry.dest

        if not src.exists():
            result.skipped.append(f"{entry.source} (未找到)")
            continue

        if src.is_file():
            if _should_exclude(src, exclude):
                result.skipped.append(f"{entry.source} (已排除)")
                continue
            dst.mkdir(parents=True, exist_ok=True)
            target = dst / src.name
            target.unlink(missing_ok=True)
            shutil.copy2(src, target)
            result.copied.append(entry.source)

        elif src.is_dir():
            _copy_dir(src, dst, exclude, result)

    return result
