"""编排器: 运行所有仓库，处理重试循环。"""
from __future__ import annotations

from pathlib import Path

from gitpush.config import Config, RepoConfig
from gitpush.filesync import sync_files
from gitpush.gitops import git_sync
from gitpush.reporter import RepoResult, print_summary, ask_retry


_STATUS_LABELS = {"ok": "成功", "no_changes": "无变更", "error": "错误"}
_STATUS_SYMBOLS = {"ok": "✓", "no_changes": "○", "error": "✗"}


def _process_repo(repo: RepoConfig, config_dir: Path) -> RepoResult:
    """对单个仓库执行同步 + git 操作，处理过程中实时输出进度。"""
    result = RepoResult(repo_name=repo.name, status="ok")

    print(f"\n── {repo.name} ──")

    try:
        # 文件同步
        if repo.files:
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

        # Git 同步
        git_result = git_sync(
            repo_path=repo.path,
            remotes=repo.remotes,
            commit_template=repo.commit_template or "update {date}",
        )
        result.git_result = git_result

        if git_result.committed:
            print(f"  已提交: {git_result.commit_message}")

        # 推送进度
        for remote in git_result.push_ok:
            print(f"  推送 {remote}... 成功")
        for remote, err in git_result.push_fail:
            print(f"  推送 {remote}... 失败 ({err})")
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
    print(f"  {symbol} {label}")

    return result


def run_all(config: Config, config_path: str | Path, verbose: bool = False) -> None:
    """运行配置中的所有仓库，打印进度和汇总，处理重试。"""
    config_dir = Path(config_path).resolve().parent
    results: list[RepoResult] = []

    print("开始同步...")

    for repo in config.repos:
        r = _process_repo(repo, config_dir)
        results.append(r)

    errored = print_summary(results)

    while errored:
        if not ask_retry():
            break
        for repo in config.repos:
            if repo.name not in errored:
                continue
            r = _process_repo(repo, config_dir)
            for i, old in enumerate(results):
                if old.repo_name == repo.name:
                    results[i] = r
                    break

        errored = print_summary(results)
