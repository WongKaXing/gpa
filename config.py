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
    with open(config_path, "rb") as f:
        raw = tomllib.load(f)

    defaults = raw.get("defaults", {})
    default_template = defaults.get("commit_template", "update {date}")
    default_exclude = defaults.get("exclude", [".DS_Store", "__pycache__", "*.pyc"])

    repos: list[RepoConfig] = []
    for repo_raw in raw.get("repos", []):
        files = [
            FileEntry(source=f["source"], dest=f["dest"])
            for f in repo_raw.get("files", [])
        ]
        repos.append(
            RepoConfig(
                name=repo_raw["name"],
                path=repo_raw["path"],
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
