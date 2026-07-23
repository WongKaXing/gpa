"""Config model and TOML parsing for gpa."""
from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class FileEntry:
    source: str
    dest: str


@dataclass
class RepoConfig:
    name: str
    path: str
    remotes: list[str]
    files: list[FileEntry] = field(default_factory=list)
    commit_template: str | None = None
    exclude: list[str] | None = None


@dataclass
class Config:
    repos: list[RepoConfig]
    commit_template: str = "update {date}"
    exclude: list[str] = field(default_factory=lambda: [".DS_Store", "__pycache__", "*.pyc"])


def parse_config(config_path: str | Path) -> Config:
    """Parse a gitpush.toml file into a Config object.

    Merges [defaults] into each repo: repo-level keys override defaults.
    """
    try:
        with open(config_path, "rb") as f:
            raw = tomllib.load(f)
    except FileNotFoundError:
        raise SystemExit(f"配置文件不存在: {config_path}")
    except PermissionError:
        raise SystemExit(f"无权限读取配置文件: {config_path}")
    except tomllib.TOMLDecodeError as e:
        raise SystemExit(f"配置文件格式错误: {e}")

    defaults = raw.get("defaults", {})
    default_template = defaults.get("commit_template", "update {date}")
    default_exclude = defaults.get("exclude", [".DS_Store", "__pycache__", "*.pyc"])

    repos: list[RepoConfig] = []
    for i, repo_raw in enumerate(raw.get("repos", []), 1):
        name = repo_raw.get("name")
        path = repo_raw.get("path")
        if not name:
            raise SystemExit(f"仓库配置 #{i} 缺少 'name' 字段")
        if not path:
            raise SystemExit(f"仓库配置 '{name}' 缺少 'path' 字段")
        files = []
        for j, f in enumerate(repo_raw.get("files", []), 1):
            source = f.get("source")
            dest = f.get("dest")
            if not source:
                raise SystemExit(f"仓库 '{name}' 的文件配置 #{j} 缺少 'source' 字段")
            if not dest:
                raise SystemExit(f"仓库 '{name}' 的文件配置 #{j} 缺少 'dest' 字段")
            files.append(FileEntry(source=source, dest=dest))
        repos.append(
            RepoConfig(
                name=name,
                path=path,
                remotes=repo_raw.get("remotes", []),
                files=files,
                commit_template=repo_raw.get("commit_template", default_template),
                exclude=repo_raw.get("exclude", default_exclude),
            )
        )

    return Config(
        repos=repos,
        commit_template=default_template,
        exclude=default_exclude,
    )
