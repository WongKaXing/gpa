"""Tests for reporter module."""
from gitpush.reporter import (
    RepoResult, _build_details, _STATUS_ICONS,
    _display_width, _pad_to, _truncate_to_width,
)


def test_display_width_ascii():
    assert _display_width("hello") == 5
    assert _display_width("") == 0


def test_display_width_chinese():
    assert _display_width("成功") == 4  # 2 chars × 2 width
    assert _display_width("无变更") == 6


def test_display_width_mixed():
    # 仓(2)+库(2)+:(1)+空格(1)+r(1)+e(1)+p(1)+o(1) = 10
    assert _display_width("仓库: repo") == 10


def test_pad_to():
    assert _pad_to("hi", 5) == "hi   "
    assert _pad_to("成功", 6) == "成功  "  # 显示宽度4, pad to 6 → 2 spaces


def test_truncate_to_width():
    assert _truncate_to_width("hello", 3) == "hel"
    assert _truncate_to_width("成功失败", 4) == "成功"  # 2 chars


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
    assert _STATUS_ICONS["ok"] == "成功"
    assert _STATUS_ICONS["no_changes"] == "无变更"
    assert _STATUS_ICONS["error"] == "错误"


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
