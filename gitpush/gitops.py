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
        result.push_fail.append(("(repo)", f"{repo} 不是一个 git 仓库"))
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
            result.push_fail.append((remote, "远程仓库未找到"))
            continue
        proc = _run(["git", "push", "-u", remote, "HEAD"], cwd=repo)
        if proc.returncode == 0:
            result.push_ok.append(remote)
        else:
            err = proc.stderr.strip().split("\n")[-1] if proc.stderr.strip() else "未知错误"
            result.push_fail.append((remote, err))

    return result
