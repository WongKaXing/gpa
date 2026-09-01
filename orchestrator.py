"""编排器: 运行所有仓库，处理重试循环。"""
from __future__ import annotations

from pathlib import Path

from gitpush.config import Config, RepoConfig
from gitpush.filesync import sync_files
from gitpush.gitops import git_sync, ensure_git_repo
from gitpush.reporter import RepoResult, print_summary, ask_retry
from gitpush.settings import order_repos
from gitpush.utils import color


_STATUS_LABELS = {"ok": "成功", "no_changes": "无变更", "error": "错误"}
_STATUS_SYMBOLS = {"ok": "✓", "no_changes": "○", "error": "✗"}
_STATUS_COLORS = {"ok": "32", "no_changes": "33", "error": "31"}


def _process_repo(repo: RepoConfig, config_dir: Path) -> RepoResult:
    """对单个仓库执行同步 + git 操作，处理过程中实时输出进度。"""
    result = RepoResult(repo_name=repo.name, status="ok")

    print(f"\n{color('── ' + repo.name + ' ──', '1')}")

    try:
        # 文件同步（files 映射 或 sync_dir 整目录同步）
        if repo.files or repo.sync_dir:
            sync_result = sync_files(repo, config_dir)
            result.sync_result = sync_result
            parts = []
            if sync_result.copied:
                parts.append(f"复制 {len(sync_result.copied)} 个文件")
            if sync_result.skipped:
                parts.append(f"跳过 {len(sync_result.skipped)} 个")
            if parts:
                print(f"  {', '.join(parts)}")
            for s in sync_result.skipped:
                if "未找到" in s:
                    result.error_details.append(f"源文件未找到: {s}")
        else:
            print(f"  (无文件配置)")

        # 确保 git 仓库已初始化（新仓库自动 git init / 远程 / 分支）
        msgs = ensure_git_repo(
            repo.path,
            repo.remotes,
            repo.remote_urls,
            repo.branch or "main",
        )
        for m in msgs:
            print(f"  {color(m, '36')}")

        # Git 同步
        git_result = git_sync(
            repo_path=repo.path,
            remotes=repo.remotes,
            commit_template=repo.commit_template or "update {date}",
        )
        result.git_result = git_result

        if git_result.committed:
            print(f"  {color('已提交', '32')}: {git_result.commit_message}")

        # 推送进度
        for remote in git_result.push_ok:
            print(f"  推送 {remote}... {color('成功', '32')}")
        for remote, err in git_result.push_fail:
            print(f"  推送 {remote}... {color('失败', '31')} ({err})")
            result.status = "error"
            result.error_details.append(f"推送失败: {remote} ({err})")

        if not git_result.committed and not git_result.push_fail and not git_result.push_ok:
            # 没有任何变更，也没推送
            pass

        if result.status == "ok" and not git_result.committed:
            if not git_result.push_fail:
                result.status = "no_changes"

    except Exception as e:
        result.status = "error"
        result.error_details.append(str(e))
        print(f"  异常: {e}")

    symbol = _STATUS_SYMBOLS.get(result.status, "?")
    label = _STATUS_LABELS.get(result.status, "?")
    code = _STATUS_COLORS.get(result.status)
    status_text = f"  {symbol} {label}"
    if code:
        status_text = color(status_text, code)
    print(status_text)

    return result


def run_all(
    config: Config,
    config_path: str | Path,
    verbose: bool = False,
    sort_order: str = "asc",
) -> None:
    """运行配置中的所有仓库，打印进度和汇总，处理重试。

    仓库处理顺序遵循设置的 sort_order（asc/desc/config）。
    """
    config_dir = Path(config_path).resolve().parent
    results: list[RepoResult] = []

    print("开始同步...")

    repos = order_repos(config.repos, sort_order)
    for repo in repos:
        r = _process_repo(repo, config_dir)
        results.append(r)

    errored = print_summary(results)

    while errored:
        if not ask_retry():
            break
        for repo in repos:
            if repo.name not in errored:
                continue
            r = _process_repo(repo, config_dir)
            for i, old in enumerate(results):
                if old.repo_name == repo.name:
                    results[i] = r
                    break

        errored = print_summary(results)


def run_single(repo: RepoConfig, config_path: str | Path) -> list[str]:
    """运行单个仓库的同步和推送。

    Args:
        repo: 要推送的仓库配置。
        config_path: 配置文件路径（用于确定配置目录）。

    Returns:
        出错的仓库名列表（空列表表示成功）。
    """
    config_dir = Path(config_path).resolve().parent
    result = _process_repo(repo, config_dir)
    return print_summary([result])
