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


def sync_files(repo: RepoConfig, config_dir: Path) -> SyncResult:
    """Copy source files/dirs into the repo, excluding matched patterns.

    Args:
        repo: RepoConfig with files, path, and exclude list.
        config_dir: Directory of the gitpush.toml, for resolving relative paths.

    Returns:
        SyncResult listing what was copied and what was skipped.
    """
    result = SyncResult()
    repo_path = _expand_path(repo.path, config_dir)
    exclude = repo.exclude or []

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
            shutil.copy2(src, dst / src.name)
            result.copied.append(entry.source)

        elif src.is_dir():
            for item in src.rglob("*"):
                if not item.is_file():
                    continue
                if _should_exclude(item, exclude):
                    result.skipped.append(str(item))
                    continue
                rel = item.relative_to(src)
                target = dst / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, target)
                result.copied.append(str(item))

    return result
