"""终端输出: 汇总表格和重试提示。"""
from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field

from gitpush.filesync import SyncResult
from gitpush.gitops import GitResult


def _display_width(text: str) -> int:
    """计算字符串的终端显示宽度（中文等宽字符计为 2）。"""
    w = 0
    for ch in text:
        ea = unicodedata.east_asian_width(ch)
        w += 2 if ea in ("W", "F") else 1
    return w


def _pad_to(text: str, width: int) -> str:
    """将字符串填充到指定显示宽度。"""
    current = _display_width(text)
    if current >= width:
        return text
    return text + " " * (width - current)


@dataclass
class RepoResult:
    repo_name: str
    status: str  # "ok", "no_changes", "error"
    sync_result: SyncResult | None = None
    git_result: GitResult | None = None
    error_details: list[str] = field(default_factory=list)


_STATUS_ICONS = {
    "ok": "成功",
    "no_changes": "无变更",
    "error": "错误",
}


def _build_details(r: RepoResult) -> str:
    parts: list[str] = []
    if r.sync_result:
        parts.append(f"已复制 {len(r.sync_result.copied)} 个文件")
        if r.sync_result.skipped:
            parts.append(f"已跳过 {len(r.sync_result.skipped)} 个")
    if r.git_result and r.git_result.committed:
        parts.append(f"已提交: {r.git_result.commit_message}")
    if r.git_result and r.git_result.push_ok:
        parts.append("已推送到 " + ", ".join(r.git_result.push_ok))
    if r.git_result and r.git_result.push_fail:
        fails = [f[0] for f in r.git_result.push_fail]
        parts.append("推送失败: " + ", ".join(fails))
    if r.error_details:
        parts.extend(r.error_details)
    return "; ".join(parts) if parts else "-"


def _format_row(name: str, status: str, details: str, widths: tuple[int, int, int]) -> str:
    w_name, w_status, w_details = widths
    return (
        f"│ {_pad_to(name, w_name)} │ "
        f"{_pad_to(status, w_status)} │ "
        f"{_pad_to(details, w_details)} │"
    )


def print_summary(results: list[RepoResult]) -> list[str]:
    """打印格式化汇总表格。

    返回出错的仓库名列表（供重试逻辑使用）。
    """
    if not results:
        print("没有需要报告的仓库。")
        return []

    # 按显示宽度计算列宽
    max_name = max(_display_width(r.repo_name) for r in results)
    w_name = max(max_name, 4)
    w_status = 10
    max_detail = max(_display_width(_build_details(r)) for r in results)
    w_details = max(max_detail, 7)

    # 限制详情列宽度，避免表格过宽
    max_table = 100
    if w_name + w_status + w_details > max_table - 10:
        w_details = max(20, max_table - 10 - w_name - w_status)

    sep = f"├{'─' * (w_name + 2)}┼{'─' * (w_status + 2)}┼{'─' * (w_details + 2)}┤"
    top = f"╭{'─' * (w_name + 2)}┬{'─' * (w_status + 2)}┬{'─' * (w_details + 2)}╮"
    bot = f"╰{'─' * (w_name + 2)}┴{'─' * (w_status + 2)}┴{'─' * (w_details + 2)}╯"

    # 标题居中（按显示宽度）
    title = "GPA 同步结果"
    inner = w_name + w_status + w_details + 4
    title_padded = f" {title} ".center(inner + _display_width(title) - len(title))

    print(top)
    print(f"│{title_padded}│")
    print(sep)
    print(_format_row("仓库", "状态", "详情", (w_name, w_status, w_details)))
    print(sep)

    errored: list[str] = []
    for r in results:
        icon = _STATUS_ICONS.get(r.status, "?")
        details = _build_details(r)
        # 截断过长详情
        if _display_width(details) > w_details:
            details = _truncate_to_width(details, w_details - 1) + "…"
        print(_format_row(r.repo_name, icon, details, (w_name, w_status, w_details)))
        if r.status == "error":
            errored.append(r.repo_name)

    print(bot)

    if errored:
        print(f"\n {len(errored)} 个仓库出错: {', '.join(errored)}")

    return errored


def _truncate_to_width(text: str, max_width: int) -> str:
    """按显示宽度截断字符串。"""
    result = ""
    w = 0
    for ch in text:
        cw = 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1
        if w + cw > max_width:
            break
        result += ch
        w += cw
    return result


def ask_retry() -> bool:
    """提示用户是否重试失败的仓库。"""
    try:
        answer = input("\n重试失败的仓库？[y/n]: ").strip().lower()
        return answer in ("y", "yes")
    except (EOFError, KeyboardInterrupt):
        print()
        return False
