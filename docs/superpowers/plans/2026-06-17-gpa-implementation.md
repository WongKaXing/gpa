# GPA (Git Push All) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a pip-installable CLI tool (`gpa`) that syncs dotfiles into Git repos and pushes to Gitee/GitHub, with an interactive first-run setup wizard.

**Architecture:** 8-module Python package. `cli.py` parses args, dispatches to `wizard.py` (first run) or `orchestrator.py` (normal run). Orchestrator calls `filesync.py` → `gitops.py` per repo, then `reporter.py` for output. `config.py` provides the TOML-backed dataclass model shared by all modules.

**Tech Stack:** Python 3.12+, stdlib only (tomllib, argparse, subprocess, shutil, pathlib, fnmatch, dataclasses). pytest for testing.

---

### Task 1: Project Structure & Package Setup

**Files:**
- Delete: `gitpush.py` (root-level, replaced by package)
- Create: `gitpush/__init__.py`
- Create: `gitpush/__main__.py`
- Modify: `pyproject.toml`

- [ ] **Step 1: Remove root-level gitpush.py and create package directory**

```bash
rm /Users/soc/Documents/PyDemo/gitpush/gitpush.py
mkdir -p /Users/soc/Documents/PyDemo/gitpush/gitpush
```

- [ ] **Step 2: Create gitpush/__init__.py**

```python
"""GPA — Git Push All: sync dotfiles to Git repos and push to multiple remotes."""
```

- [ ] **Step 3: Create gitpush/__main__.py**

```python
"""Allow running via python -m gitpush."""
from gitpush.cli import main

main()
```

- [ ] **Step 4: Update pyproject.toml with entry point and pytest dependency**

Read the file, then replace with:

```toml
[project]
name = "gitpush"
version = "0.1.0"
description = "Sync dotfiles to Git repos and push to multiple remotes"
readme = "README.md"
requires-python = ">=3.12"
dependencies = []

[project.optional-dependencies]
dev = ["pytest>=8"]

[project.scripts]
gpa = "gitpush.cli:main"
```

- [ ] **Step 5: Verify package is importable**

```bash
cd /Users/soc/Documents/PyDemo/gitpush && python -c "from gitpush import __doc__; print(__doc__)"
```

Expected: prints "GPA — Git Push All..."

- [ ] **Step 6: Commit**

```bash
cd /Users/soc/Documents/PyDemo/gitpush && git add -A && git commit -m "feat: set up gitpush package structure with entry point"
```

---

### Task 2: Config Dataclasses & TOML Parsing

**Files:**
- Create: `gitpush/config.py`
- Create: `tests/__init__.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Create gitpush/config.py with dataclasses**

```python
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
```

- [ ] **Step 2: Create tests/test_config.py**

```python
"""Tests for config parsing."""
import tempfile
from pathlib import Path
from gitpush.config import parse_config, Config, RepoConfig, FileEntry


def test_parse_minimal_config():
    toml = """
[[repos]]
name = "test"
path = "/tmp/test"
remotes = ["origin"]
"""
    with tempfile.NamedTemporaryFile(mode="wb", suffix=".toml", delete=False) as f:
        f.write(toml.encode())
        tmp = Path(f.name)

    try:
        cfg = parse_config(tmp)
        assert len(cfg.repos) == 1
        assert cfg.repos[0].name == "test"
        assert cfg.repos[0].path == "/tmp/test"
        assert cfg.repos[0].remotes == ["origin"]
        assert cfg.repos[0].files == []
        assert cfg.repos[0].commit_template == "update {date}"
        assert cfg.repos[0].exclude == [".DS_Store", "__pycache__", "*.pyc"]
    finally:
        tmp.unlink()


def test_parse_with_files():
    toml = """
[[repos]]
name = "dots"
path = "~/dots"
remotes = ["gitee", "github"]

[[repos.files]]
source = "~/.config/nvim"
dest = "./"

[[repos.files]]
source = "~/.zshrc"
dest = "."
"""
    with tempfile.NamedTemporaryFile(mode="wb", suffix=".toml", delete=False) as f:
        f.write(toml.encode())
        tmp = Path(f.name)

    try:
        cfg = parse_config(tmp)
        assert len(cfg.repos[0].files) == 2
        assert cfg.repos[0].files[0].source == "~/.config/nvim"
        assert cfg.repos[0].files[1].dest == "."
    finally:
        tmp.unlink()


def test_defaults_override():
    toml = """
[defaults]
commit_template = "custom {date}"
exclude = [".git", "*.swp"]

[[repos]]
name = "a"
path = "/tmp/a"
remotes = []

[[repos]]
name = "b"
path = "/tmp/b"
remotes = []
commit_template = "override {date}"
"""
    with tempfile.NamedTemporaryFile(mode="wb", suffix=".toml", delete=False) as f:
        f.write(toml.encode())
        tmp = Path(f.name)

    try:
        cfg = parse_config(tmp)
        assert cfg.repos[0].commit_template == "custom {date}"
        assert cfg.repos[0].exclude == [".git", "*.swp"]
        assert cfg.repos[1].commit_template == "override {date}"
    finally:
        tmp.unlink()


def test_default_commit_template():
    cfg = Config(repos=[])
    assert cfg.commit_template == "update {date}"


def test_default_exclude():
    cfg = Config(repos=[])
    assert ".DS_Store" in cfg.exclude
    assert "__pycache__" in cfg.exclude
```

- [ ] **Step 3: Run tests and verify they pass**

```bash
cd /Users/soc/Documents/PyDemo/gitpush && python -m pytest tests/test_config.py -v
```

Expected: 4 tests pass

- [ ] **Step 4: Commit**

```bash
cd /Users/soc/Documents/PyDemo/gitpush && git add gitpush/config.py tests/ && git commit -m "feat: add config dataclasses and TOML parser"
```

---

### Task 3: File Sync with Glob Exclusion

**Files:**
- Create: `gitpush/filesync.py`
- Create: `tests/test_filesync.py`

- [ ] **Step 1: Create gitpush/filesync.py**

```python
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
            result.skipped.append(f"{entry.source} (not found)")
            continue

        if src.is_file():
            if _should_exclude(src, exclude):
                result.skipped.append(f"{entry.source} (excluded)")
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
```

- [ ] **Step 2: Create tests/test_filesync.py**

```python
"""Tests for file sync with exclusion."""
import tempfile
from pathlib import Path
from gitpush.config import RepoConfig, FileEntry
from gitpush.filesync import sync_files, _should_exclude


def test_should_exclude_by_name():
    assert _should_exclude(Path("/tmp/.DS_Store"), [".DS_Store"]) is True
    assert _should_exclude(Path("/tmp/real.txt"), [".DS_Store"]) is False


def test_should_exclude_by_pattern():
    assert _should_exclude(Path("/tmp/file.pyc"), ["*.pyc"]) is True
    assert _should_exclude(Path("/tmp/file.py"), ["*.pyc"]) is False


def test_sync_single_file():
    with tempfile.TemporaryDirectory() as src_dir:
        with tempfile.TemporaryDirectory() as repo_dir:
            src = Path(src_dir) / "hello.txt"
            src.write_text("hello")

            repo = RepoConfig(
                name="test",
                path=repo_dir,
                remotes=[],
                files=[FileEntry(source=str(src_dir), dest=".")],
                exclude=[],
            )

            result = sync_files(repo, Path("."))
            assert len(result.copied) >= 1
            assert (Path(repo_dir) / "hello.txt").exists()


def test_sync_skips_excluded_file():
    with tempfile.TemporaryDirectory() as src_dir:
        with tempfile.TemporaryDirectory() as repo_dir:
            (Path(src_dir) / "good.txt").write_text("ok")
            (Path(src_dir) / ".DS_Store").write_text("junk")

            repo = RepoConfig(
                name="test",
                path=repo_dir,
                remotes=[],
                files=[FileEntry(source=str(src_dir), dest=".")],
                exclude=[".DS_Store"],
            )

            result = sync_files(repo, Path("."))
            skipped = [s for s in result.skipped if ".DS_Store" in s]
            assert len(skipped) == 1
            assert not (Path(repo_dir) / ".DS_Store").exists()


def test_sync_missing_source():
    repo = RepoConfig(
        name="test",
        path="/tmp/repo",
        remotes=[],
        files=[FileEntry(source="/nonexistent/path", dest=".")],
        exclude=[],
    )

    result = sync_files(repo, Path("."))
    assert len(result.copied) == 0
    assert any("not found" in s for s in result.skipped)


def test_sync_nested_directory():
    with tempfile.TemporaryDirectory() as src_dir:
        with tempfile.TemporaryDirectory() as repo_dir:
            nested = Path(src_dir) / "sub" / "deep"
            nested.mkdir(parents=True)
            (Path(src_dir) / "top.txt").write_text("top")
            (nested / "deep.txt").write_text("deep")

            repo = RepoConfig(
                name="test",
                path=repo_dir,
                remotes=[],
                files=[FileEntry(source=str(src_dir), dest=".")],
                exclude=[],
            )

            result = sync_files(repo, Path("."))
            assert len(result.copied) == 2
            assert (Path(repo_dir) / "top.txt").exists()
            assert (Path(repo_dir) / "sub" / "deep" / "deep.txt").exists()
```

- [ ] **Step 3: Run tests**

```bash
cd /Users/soc/Documents/PyDemo/gitpush && python -m pytest tests/test_filesync.py -v
```

Expected: 5 tests pass

- [ ] **Step 4: Commit**

```bash
cd /Users/soc/Documents/PyDemo/gitpush && git add gitpush/filesync.py tests/test_filesync.py && git commit -m "feat: add file sync with glob-based exclusion"
```

---

### Task 4: Git Operations (add, commit, push)

**Files:**
- Create: `gitpush/gitops.py`
- Create: `tests/test_gitops.py`

- [ ] **Step 1: Create gitpush/gitops.py**

```python
"""Git operations: add, commit, push via subprocess."""
from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path


@dataclass
class GitResult:
    committed: bool = False
    commit_message: str = ""
    push_ok: list[str] = field(default_factory=list)
    push_fail: list[tuple[str, str]] = field(default_factory=list)


def _run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd, cwd=cwd, capture_output=True, text=True
    )


def _remote_exists(name: str, repo_path: Path) -> bool:
    result = _run(["git", "remote"], cwd=repo_path)
    return name in result.stdout.splitlines()


def _has_staged_changes(repo_path: Path) -> bool:
    result = _run(["git", "diff", "--cached", "--quiet"], cwd=repo_path)
    return result.returncode != 0


def _fill_template(template: str) -> str:
    return template.format(date=date.today().isoformat())


def git_sync(
    repo_path: str | Path,
    remotes: list[str],
    commit_template: str,
) -> GitResult:
    """Stage all changes, commit if any, then push to each remote.

    Args:
        repo_path: Path to the Git repository.
        remotes: List of remote names to push to.
        commit_template: Template string with {date} placeholder.

    Returns:
        GitResult with commit/push status.
    """
    result = GitResult()
    repo = Path(repo_path).expanduser().resolve()

    if not (repo / ".git").exists():
        result.push_fail.append(("(repo)", f"{repo} is not a git repository"))
        return result

    _run(["git", "add", "-A"], cwd=repo)

    if _has_staged_changes(repo):
        msg = _fill_template(commit_template)
        _run(["git", "commit", "-m", msg], cwd=repo)
        result.committed = True
        result.commit_message = msg
    else:
        return result

    for remote in remotes:
        if not _remote_exists(remote, repo):
            result.push_fail.append((remote, "remote not found"))
            continue
        proc = _run(["git", "push", remote], cwd=repo)
        if proc.returncode == 0:
            result.push_ok.append(remote)
        else:
            err = proc.stderr.strip().split("\n")[-1] if proc.stderr.strip() else "unknown error"
            result.push_fail.append((remote, err))

    return result
```

- [ ] **Step 2: Create tests/test_gitops.py**

```python
"""Tests for git operations."""
import tempfile
import subprocess
from pathlib import Path
from datetime import date
from gitpush.gitops import git_sync, _fill_template, _has_staged_changes


def _init_repo(path: Path) -> None:
    subprocess.run(["git", "init"], cwd=path, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=path, capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=path, capture_output=True,
    )
    # Create an initial commit so there's a branch to push from
    (path / "initial.txt").write_text("init")
    subprocess.run(["git", "add", "-A"], cwd=path, capture_output=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=path, capture_output=True)


def _init_bare_repo(path: Path) -> None:
    subprocess.run(["git", "init", "--bare", str(path)], capture_output=True)


def test_fill_template():
    result = _fill_template("update {date}")
    assert date.today().isoformat() in result


def test_fill_template_custom():
    result = _fill_template("backup {date}")
    assert result.startswith("backup ")


def test_no_changes_no_commit():
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        _init_repo(repo)
        result = git_sync(repo, remotes=[], commit_template="update {date}")
        assert result.committed is False


def test_commit_when_changes():
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        _init_repo(repo)
        (repo / "new.txt").write_text("changed")
        result = git_sync(repo, remotes=[], commit_template="update {date}")
        assert result.committed is True


def test_push_to_remote():
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp) / "local"
        repo.mkdir()
        _init_repo(repo)

        bare = Path(tmp) / "bare.git"
        bare.mkdir()
        _init_bare_repo(bare)

        subprocess.run(
            ["git", "remote", "add", "origin", str(bare)],
            cwd=repo, capture_output=True,
        )

        (repo / "new.txt").write_text("push me")
        result = git_sync(repo, remotes=["origin"], commit_template="update {date}")
        assert result.committed is True
        assert "origin" in result.push_ok
        assert len(result.push_fail) == 0


def test_push_missing_remote():
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        _init_repo(repo)
        (repo / "new.txt").write_text("test")
        result = git_sync(repo, remotes=["nonexistent"], commit_template="update {date}")
        assert len(result.push_fail) == 1
        assert result.push_fail[0][0] == "nonexistent"
```

- [ ] **Step 3: Run tests**

```bash
cd /Users/soc/Documents/PyDemo/gitpush && python -m pytest tests/test_gitops.py -v
```

Expected: 6 tests pass

- [ ] **Step 4: Commit**

```bash
cd /Users/soc/Documents/PyDemo/gitpush && git add gitpush/gitops.py tests/test_gitops.py && git commit -m "feat: add git operations (add, commit, push)"
```

---

### Task 5: Reporter — Pretty Output & Retry Prompt

**Files:**
- Create: `gitpush/reporter.py`
- Create: `tests/test_reporter.py`

- [ ] **Step 1: Create gitpush/reporter.py**

```python
"""Terminal output: summary table and retry prompt."""
from __future__ import annotations

from dataclasses import dataclass, field

from gitpush.filesync import SyncResult
from gitpush.gitops import GitResult


@dataclass
class RepoResult:
    repo_name: str
    status: str  # "ok", "no_changes", "error"
    sync_result: SyncResult | None = None
    git_result: GitResult | None = None
    error_details: list[str] = field(default_factory=list)


_STATUS_ICONS = {
    "ok": "OK",
    "no_changes": "NO CHANGES",
    "error": "ERROR",
}


def _build_details(r: RepoResult) -> str:
    parts: list[str] = []
    if r.sync_result:
        parts.append(f"copied {len(r.sync_result.copied)} file(s)")
        if r.sync_result.skipped:
            parts.append(f"skipped {len(r.sync_result.skipped)}")
    if r.git_result and r.git_result.committed:
        parts.append(f"committed: {r.git_result.commit_message}")
    if r.git_result and r.git_result.push_ok:
        parts.append("pushed to " + ", ".join(r.git_result.push_ok))
    if r.git_result and r.git_result.push_fail:
        fails = [f[0] for f in r.git_result.push_fail]
        parts.append("push failed: " + ", ".join(fails))
    if r.error_details:
        parts.extend(r.error_details)
    return "; ".join(parts) if parts else "-"


def _format_row(name: str, status: str, details: str, widths: tuple[int, int, int]) -> str:
    w_name, w_status, w_details = widths
    return f"│ {name:<{w_name}} │ {status:<{w_status}} │ {details:<{w_details}} │"


def print_summary(results: list[RepoResult]) -> list[str]:
    """Print a formatted summary table.

    Returns list of errored repo names (for retry logic).
    """
    if not results:
        print("No repos to report.")
        return []

    # Calculate column widths
    max_name = max(len(r.repo_name) for r in results)
    w_name = max(max_name, 4)
    w_status = 12
    max_detail = max(len(_build_details(r)) for r in results)
    w_details = max(max_detail, 7)

    sep = f"├{'─' * (w_name + 2)}┼{'─' * (w_status + 2)}┼{'─' * (w_details + 2)}┤"
    top = f"╭{'─' * (w_name + 2)}┬{'─' * (w_status + 2)}┬{'─' * (w_details + 2)}╮"
    bot = f"╰{'─' * (w_name + 2)}┴{'─' * (w_status + 2)}┴{'─' * (w_details + 2)}╯"

    print(top)
    print(f"│ {'GPA Sync Result':^{w_name + w_status + w_details + 4}} │")
    print(sep)
    print(_format_row("Repo", "Status", "Details", (w_name, w_status, w_details)))
    print(sep)

    errored: list[str] = []
    for r in results:
        icon = _STATUS_ICONS.get(r.status, "?")
        details = _build_details(r)
        print(_format_row(r.repo_name, icon, details, (w_name, w_status, w_details)))
        if r.status == "error":
            errored.append(r.repo_name)

    print(bot)

    if errored:
        print(f"\n Errors in {len(errored)} repo(s): {', '.join(errored)}")

    return errored


def ask_retry() -> bool:
    """Prompt user whether to retry failed repos."""
    try:
        answer = input("\nRetry failed repos? [y/n]: ").strip().lower()
        return answer in ("y", "yes")
    except (EOFError, KeyboardInterrupt):
        print()
        return False
```

- [ ] **Step 2: Create tests/test_reporter.py**

```python
"""Tests for reporter module."""
from gitpush.reporter import RepoResult, _build_details, _STATUS_ICONS


def test_build_details_ok():
    r = RepoResult(repo_name="test", status="ok")
    details = _build_details(r)
    assert details == "-"


def test_build_details_no_changes():
    r = RepoResult(repo_name="test", status="no_changes")
    details = _build_details(r)
    assert details == "-"


def test_build_details_with_error():
    r = RepoResult(
        repo_name="test",
        status="error",
        error_details=["push failed: github (auth)"],
    )
    details = _build_details(r)
    assert "push failed" in details


def test_status_icons_present():
    assert _STATUS_ICONS["ok"] == "OK"
    assert _STATUS_ICONS["no_changes"] == "NO CHANGES"
    assert _STATUS_ICONS["error"] == "ERROR"


def test_print_summary_empty():
    from gitpush.reporter import print_summary
    errored = print_summary([])
    assert errored == []


def test_print_summary_returns_errored(capsys):
    from gitpush.reporter import print_summary
    results = [
        RepoResult(repo_name="good", status="ok"),
        RepoResult(repo_name="bad", status="error", error_details=["fail"]),
    ]
    errored = print_summary(results)
    assert errored == ["bad"]
```

- [ ] **Step 3: Run tests**

```bash
cd /Users/soc/Documents/PyDemo/gitpush && python -m pytest tests/test_reporter.py -v
```

Expected: 6 tests pass

- [ ] **Step 4: Commit**

```bash
cd /Users/soc/Documents/PyDemo/gitpush && git add gitpush/reporter.py tests/test_reporter.py && git commit -m "feat: add reporter with pretty table output and retry prompt"
```

---

### Task 6: Interactive Setup Wizard

**Files:**
- Create: `gitpush/wizard.py`

- [ ] **Step 1: Create gitpush/wizard.py**

```python
"""Interactive setup wizard — generates gitpush.toml on first run."""
from __future__ import annotations

import subprocess
from pathlib import Path


def _input(prompt: str) -> str:
    """Wrapper for input that handles EOF/KeyboardInterrupt gracefully."""
    try:
        return input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        print("\nAborted.")
        raise SystemExit(0)


def _scan_directory(path: str) -> list[str]:
    """List all entries in a directory."""
    p = Path(path).expanduser().resolve()
    if not p.exists() or not p.is_dir():
        print(f"  Directory not found: {p}")
        return []
    entries = sorted(
        [e.name for e in p.iterdir()],
        key=str.lower,
    )
    return entries


def _select_items(entries: list[str]) -> list[str]:
    """Display numbered list, return user-selected item names."""
    for i, name in enumerate(entries, 1):
        is_dir = " (dir)" if not name.startswith(".") else ""
        print(f"  {i}. {name}{is_dir}")

    choice = _input(f"Select items to sync (comma-separated numbers, or 'all'): ")
    if choice.lower() == "all":
        return entries

    selected: list[str] = []
    indices: list[int] = []
    for part in choice.split(","):
        part = part.strip()
        try:
            idx = int(part) - 1
            if 0 <= idx < len(entries):
                indices.append(idx)
        except ValueError:
            # Try matching by name
            matching = [e for e in entries if e.lower() == part.lower()]
            if matching:
                for m in matching:
                    if m not in selected:
                        selected.append(m)
            continue

    for idx in sorted(set(indices)):
        if entries[idx] not in selected:
            selected.append(entries[idx])

    return selected


def _detect_remotes(repo_path: str) -> dict[str, str | None]:
    """Run git remote -v and return dict of remote_name -> fetch_url or None."""
    p = Path(repo_path).expanduser().resolve()
    if not (p / ".git").exists():
        return {}
    result = subprocess.run(
        ["git", "remote", "-v"],
        cwd=p, capture_output=True, text=True,
    )
    remotes: dict[str, str | None] = {}
    for line in result.stdout.splitlines():
        if "(fetch)" in line:
            parts = line.split()
            if len(parts) >= 2:
                remotes[parts[0]] = parts[1]
    return remotes


def _configure_remote(repo_path: str, remote_name: str) -> str | None:
    """If remote_name exists, return it. Otherwise prompt to add it."""
    remotes = _detect_remotes(repo_path)
    if remote_name in remotes:
        print(f"  Detected existing remote: {remote_name} → {remotes[remote_name]}")
        return remote_name

    url = _input(f"  {remote_name} remote not found. Enter URL (or 'None' to skip): ")
    if url.lower() == "none" or not url:
        return None

    p = Path(repo_path).expanduser().resolve()
    subprocess.run(
        ["git", "remote", "add", remote_name, url],
        cwd=p, capture_output=True,
    )
    print(f"  Added remote: {remote_name} → {url}")
    return remote_name


def run_wizard(config_path: str | Path = "gitpush.toml") -> None:
    """Run interactive setup and write gitpush.toml."""
    config_path = Path(config_path)

    print("╭──────────────────────────────────────────────╮")
    print("│        GPA — Interactive Setup Wizard        │")
    print("╰──────────────────────────────────────────────╯\n")

    commit_template = _input(
        "Commit message template? (default: 'update {date}'): "
    )
    if not commit_template:
        commit_template = "update {date}"

    exclude_input = _input(
        "Exclude glob patterns? (default: .DS_Store, __pycache__, *.pyc): "
    )
    if not exclude_input:
        exclude = [".DS_Store", "__pycache__", "*.pyc"]
    else:
        exclude = [p.strip() for p in exclude_input.split(",") if p.strip()]

    # Build TOML content
    lines: list[str] = []
    lines.append("[defaults]")
    lines.append(f'commit_template = "{commit_template}"')
    exclude_toml = ", ".join(f'"{e}"' for e in exclude)
    lines.append(f"exclude = [{exclude_toml}]")
    lines.append("")

    repo_count = 0
    while True:
        repo_count += 1
        print(f"\n── Repo #{repo_count} ──")

        source = _input("Enter source directory to scan (e.g. ~/.config, or 'None' to skip copy): ")
        selected: list[str] = []
        source_path = ""

        if source.lower() != "none" and source:
            source_path = source
            entries = _scan_directory(source)
            if entries:
                selected = _select_items(entries)
                print(f"  Selected: {', '.join(selected)}")
                modify = _input("  Modify selection? [y/N]: ")
                if modify.lower() in ("y", "yes"):
                    selected = _select_items(entries)
                    print(f"  Updated selection: {', '.join(selected)}")
            else:
                print("  No entries found in directory.")

        upload = _input("Enter Git repo directory to sync into: ")
        if not upload:
            print("  Skipping — no repo path provided.")
            continue

        remotes: list[str] = []
        for name in ("gitee", "github"):
            r = _configure_remote(upload, name)
            if r:
                remotes.append(r)

        name = Path(upload).expanduser().name
        lines.append("[[repos]]")
        lines.append(f'name = "{name}"')
        lines.append(f'path = "{upload}"')
        remotes_toml = ", ".join(f'"{r}"' for r in remotes)
        lines.append(f"remotes = [{remotes_toml}]")
        lines.append("")

        for item in selected:
            item_source = str(Path(source_path).expanduser() / item)
            lines.append("[[repos.files]]")
            lines.append(f'source = "{item_source}"')
            lines.append(f'dest = "."')
            lines.append("")

        again = _input("\nAdd another repo? [y/N]: ")
        if again.lower() not in ("y", "yes"):
            break

    config_path.write_text("\n".join(lines) + "\n")
    print(f"\n Config written to {config_path.resolve()}")
```

- [ ] **Step 2: Verify wizard module is importable**

```bash
cd /Users/soc/Documents/PyDemo/gitpush && python -c "from gitpush.wizard import run_wizard; print('ok')"
```

Expected: prints "ok"

- [ ] **Step 3: Commit**

```bash
cd /Users/soc/Documents/PyDemo/gitpush && git add gitpush/wizard.py && git commit -m "feat: add interactive setup wizard"
```

---

### Task 7: Orchestrator — Tie Modules Together

**Files:**
- Create: `gitpush/orchestrator.py`

- [ ] **Step 1: Create gitpush/orchestrator.py**

```python
"""Orchestrator: run all repos, handle retry loop."""
from __future__ import annotations

from pathlib import Path

from gitpush.config import Config, RepoConfig
from gitpush.filesync import sync_files
from gitpush.gitops import git_sync
from gitpush.reporter import RepoResult, print_summary, ask_retry


def _process_repo(repo: RepoConfig, config_dir: Path) -> RepoResult:
    """Run sync + git ops for a single repo, return RepoResult."""
    result = RepoResult(repo_name=repo.name, status="ok")

    try:
        # File sync
        if repo.files:
            sync_result = sync_files(repo, config_dir)
            result.sync_result = sync_result
            if sync_result.skipped:
                for s in sync_result.skipped:
                    if "not found" in s:
                        result.error_details.append(f"source not found: {s}")

        # Git sync
        git_result = git_sync(
            repo_path=repo.path,
            remotes=repo.remotes,
            commit_template=repo.commit_template or "update {date}",
        )
        result.git_result = git_result

        if git_result.push_fail:
            result.status = "error"
            for remote, err in git_result.push_fail:
                result.error_details.append(f"push failed: {remote} ({err})")

        if result.status == "ok" and not git_result.committed:
            if not git_result.push_fail:
                result.status = "no_changes"

    except Exception as e:
        result.status = "error"
        result.error_details.append(str(e))

    return result


def run_all(config: Config, config_path: str | Path, verbose: bool = False) -> None:
    """Run all repos in config, print summary, handle retry."""
    config_dir = Path(config_path).resolve().parent
    results: list[RepoResult] = []

    for repo in config.repos:
        if verbose:
            print(f"\n Processing: {repo.name} ({repo.path})")
        r = _process_repo(repo, config_dir)
        results.append(r)
        if verbose:
            status_icon = {"ok": "OK", "no_changes": "NO CHANGES", "error": "ERROR"}[r.status]
            print(f"   → {status_icon}")

    errored = print_summary(results)

    while errored:
        if not ask_retry():
            break
        # Retry only errored repos
        for repo in config.repos:
            if repo.name not in errored:
                continue
            if verbose:
                print(f"\n Retrying: {repo.name}")
            r = _process_repo(repo, config_dir)
            # Replace old result
            for i, old in enumerate(results):
                if old.repo_name == repo.name:
                    results[i] = r
                    break
            if verbose:
                status_icon = {"ok": "OK", "no_changes": "NO CHANGES", "error": "ERROR"}[r.status]
                print(f"   → {status_icon}")

        errored = print_summary(results)
```

- [ ] **Step 2: Verify import**

```bash
cd /Users/soc/Documents/PyDemo/gitpush && python -c "from gitpush.orchestrator import run_all; print('ok')"
```

Expected: prints "ok"

- [ ] **Step 3: Commit**

```bash
cd /Users/soc/Documents/PyDemo/gitpush && git add gitpush/orchestrator.py && git commit -m "feat: add orchestrator with retry logic"
```

---

### Task 8: CLI Entry Point

**Files:**
- Create: `gitpush/cli.py`

- [ ] **Step 1: Create gitpush/cli.py**

```python
"""CLI entry point for the gpa command."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from gitpush.config import parse_config
from gitpush.orchestrator import run_all
from gitpush.wizard import run_wizard


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="gpa",
        description="Git Push All — sync dotfiles to Git repos and push to multiple remotes",
    )
    parser.add_argument(
        "-c", "--config",
        default="gitpush.toml",
        help="Path to config file (default: ./gitpush.toml)",
    )
    parser.add_argument(
        "action",
        nargs="?",
        default=None,
        help="'init' to re-run setup wizard",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview only, no changes",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output",
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Quiet mode, only errors",
    )

    args = parser.parse_args()

    if args.action == "init":
        run_wizard(args.config)
        return

    config_path = Path(args.config)

    if not config_path.exists():
        print(f"No config found at {config_path}. Starting setup wizard...\n")
        run_wizard(config_path)
        if not config_path.exists():
            print("Setup cancelled. Exiting.")
            sys.exit(0)

    config = parse_config(config_path)

    if args.dry_run:
        print(f"Dry run — would process {len(config.repos)} repo(s):")
        for repo in config.repos:
            print(f"  [{repo.name}] {repo.path} → remotes: {repo.remotes}")
            for f in repo.files:
                print(f"    copy: {f.source} → {f.dest}")
        return

    run_all(config, config_path, verbose=args.verbose)
```

- [ ] **Step 2: Test CLI --help**

```bash
cd /Users/soc/Documents/PyDemo/gitpush && python -m gitpush --help
```

Expected: prints help text with `gpa` as program name

- [ ] **Step 3: Test CLI dry-run with a sample config**

Create a temporary config and test:

```bash
cd /Users/soc/Documents/PyDemo/gitpush && cat > /tmp/test_gpa.toml << 'TOML'
[defaults]
commit_template = "update {date}"
exclude = [".DS_Store", "__pycache__", "*.pyc"]

[[repos]]
name = "test"
path = "/tmp/test_repo"
remotes = ["gitee", "github"]

[[repos.files]]
source = "/tmp/test_src"
dest = "."
TOML
python -m gitpush -c /tmp/test_gpa.toml --dry-run
```

Expected: prints dry-run summary

- [ ] **Step 4: Test gpa command via pip install**

```bash
cd /Users/soc/Documents/PyDemo/gitpush && pip install -e . && gpa --help
```

Expected: prints help text

- [ ] **Step 5: Commit**

```bash
cd /Users/soc/Documents/PyDemo/gitpush && git add gitpush/cli.py && git commit -m "feat: add CLI entry point with argparse"
```

---

### Task 9: Integration Test — Full End-to-End

**Files:**
- Create: `tests/test_integration.py`

- [ ] **Step 1: Create tests/test_integration.py**

```python
"""End-to-end integration tests with real git repos."""
import subprocess
import tempfile
from pathlib import Path
from gitpush.config import parse_config
from gitpush.orchestrator import run_all


def _init_repo(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init"], cwd=path, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=path, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=path, capture_output=True)
    (path / ".keep").write_text("")
    subprocess.run(["git", "add", "-A"], cwd=path, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=path, capture_output=True)


def _init_bare(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "--bare", str(path)], capture_output=True)


def test_full_flow_with_push():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)

        # Setup source files
        src = tmp / "configs"
        src.mkdir()
        (src / "starship.toml").write_text("format = '$all'")
        (src / ".DS_Store").write_text("junk")
        sub_src = src / "nvim"
        sub_src.mkdir()
        (sub_src / "init.lua").write_text("vim.opt.number = true")

        # Setup git repo
        repo = tmp / "dots"
        _init_repo(repo)

        # Setup bare remote
        bare = tmp / "bare.git"
        _init_bare(bare)
        subprocess.run(
            ["git", "remote", "add", "origin", str(bare)],
            cwd=repo, capture_output=True,
        )

        # Write config
        config_toml = f"""
[defaults]
commit_template = "update {{date}}"
exclude = [".DS_Store"]

[[repos]]
name = "dots"
path = "{repo}"
remotes = ["origin"]

[[repos.files]]
source = "{src}"
dest = "."
"""
        config_path = tmp / "gitpush.toml"
        config_path.write_text(config_toml)

        # Run
        config = parse_config(config_path)
        run_all(config, config_path, verbose=True)

        # Verify files were copied (excluding .DS_Store)
        assert (repo / "starship.toml").exists()
        assert (repo / "nvim" / "init.lua").exists()
        assert not (repo / ".DS_Store").exists()

        # Verify commit was made
        log = subprocess.run(
            ["git", "log", "--oneline"],
            cwd=repo, capture_output=True, text=True,
        )
        assert "update" in log.stdout
```

- [ ] **Step 2: Run integration test**

```bash
cd /Users/soc/Documents/PyDemo/gitpush && python -m pytest tests/test_integration.py -v
```

Expected: 1 test passes

- [ ] **Step 3: Run all tests**

```bash
cd /Users/soc/Documents/PyDemo/gitpush && python -m pytest tests/ -v
```

Expected: all 22 tests pass

- [ ] **Step 4: Final commit**

```bash
cd /Users/soc/Documents/PyDemo/gitpush && git add tests/test_integration.py && git commit -m "test: add end-to-end integration test"
```
