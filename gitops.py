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


def ensure_git_repo(
    repo_path: str | Path,
    remotes: list[str],
    remote_urls: dict[str, str] | None = None,
    branch: str = "main",
) -> list[str]:
    """确保路径已初始化为 git 仓库，且远程与分支与配置一致。

    用于新仓库自动构建（git init + 添加远程 + 切分支）以及
    现有仓库的远程/分支校正。返回提示信息列表（不抛异常）。

    Args:
        repo_path: 仓库目录（不存在时会创建）。
        remotes: 配置的远程名称列表（有 URL 的优先用 URL）。
        remote_urls: 远程名 -> URL 映射（[[repos.remotes]] url 字段）。
        branch: 目标分支（默认 main）。
    """
    msgs: list[str] = []
    repo = Path(repo_path).expanduser().resolve()
    remote_urls = remote_urls or {}

    if not (repo / ".git").exists():
        repo.mkdir(parents=True, exist_ok=True)
        # git init -b 需要 git >= 2.28，低版本回退 init + checkout -b
        proc = _run(["git", "init", "-b", branch], cwd=repo)
        if proc.returncode != 0:
            _run(["git", "init"], cwd=repo)
            _run(["git", "checkout", "-b", branch], cwd=repo)
        msgs.append(f"已初始化 git 仓库 (分支 {branch})")

    existing = _run(["git", "remote"], cwd=repo).stdout.splitlines()
    for name in remotes:
        url = remote_urls.get(name)
        if name in existing:
            if url:
                cur = _run(["git", "remote", "get-url", name], cwd=repo).stdout.strip()
                if cur != url:
                    _run(["git", "remote", "set-url", name, url], cwd=repo)
                    msgs.append(f"远程 {name} URL 已更新")
        else:
            if url:
                _run(["git", "remote", "add", name, url], cwd=repo)
                msgs.append(f"已添加远程 {name}")
            else:
                msgs.append(f"远程 {name} 未配置 URL，请在 ~/.gitpush.toml 的 [[repos.remotes]] 中补充")

    # 分支校正
    cur_branch = _run(["git", "branch", "--show-current"], cwd=repo).stdout.strip()
    if cur_branch and cur_branch != branch:
        proc = _run(["git", "checkout", branch], cwd=repo)
        if proc.returncode != 0:
            _run(["git", "checkout", "-b", branch], cwd=repo)
        msgs.append(f"已切换到分支 {branch}")

    return msgs


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
