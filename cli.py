"""gpa 命令的 CLI 入口。"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from gitpush.config import parse_config, Config
from gitpush.orchestrator import run_all, run_single
from gitpush.state import load_config_path, save_config_path
from gitpush.wizard import (
    run_wizard, append_repo_to_config,
    delete_repo_from_config, reconfigure_repo_in_config,
)

_SEP = "─" * 48
_THIN = "╌" * 48


def _get_config_path() -> Path | None:
    """获取配置文件路径，如果不存在则打印错误信息并返回 None。"""
    saved_path = load_config_path()
    if saved_path is None:
        print("未找到已保存的配置。")
        print("运行 'gpa init' 创建配置，或使用 -c 参数指定配置文件。")
        return None
    config_path = Path(saved_path)
    if not config_path.exists():
        print(f"已保存的配置文件不存在: {config_path}")
        print("运行 'gpa init' 重新创建配置。")
        return None
    return config_path


def _resolve_config(
    config_arg: str | None,
    save: bool = True,
) -> tuple[Path, Config] | None:
    """解析配置文件路径并加载配置。

    Args:
        config_arg: -c 参数指定的配置文件路径，可能为 None。
        save: 是否保存配置路径到状态文件（默认 True）。

    Returns:
        (config_path, config) 元组，或 None 表示失败。
    """
    if config_arg:
        config_path = Path(config_arg)
        if not config_path.exists():
            print(f"未找到配置文件: {config_path}")
            print("运行 'gpa init' 创建配置，或检查路径是否正确。")
            return None
        if save:
            save_config_path(config_path)
    else:
        config_path = _get_config_path()
        if config_path is None:
            return None
    config = parse_config(config_path)
    return config_path, config


def _clear_screen() -> None:
    """清屏。"""
    print("\033[2J\033[H", end="")


def _print_banner() -> None:
    """打印 gpa 命令说明。"""
    print()
    print("╭" + "─" * 50 + "╮")
    print("│  GPA — Git Push All" + " " * 31 + "│")
    print("│  同步文件到 Git 仓库并推送到多个远程仓库" + " " * 15 + "│")
    print("╰" + "─" * 50 + "╯")
    print()
    print("  用法:")
    print("    gpa              检测已有配置，进入交互菜单")
    print("    gpa init         首次运行，创建配置文件")
    print("    gpa -c <路径>    指定配置文件直接执行推送")
    print()
    print("  配置文件:")
    print(f"    默认位置: ~/.gitpush.toml")
    print(f"    状态文件: ~/.config/gitpush/state.json")
    print(f"    可直接编辑 TOML 文件来修改仓库配置")
    print()
    print("  可选参数:")
    print("    --dry-run        仅预览，不实际执行")
    print("    -v, --verbose    详细输出每个仓库的处理过程")
    print("    -q, --quiet      静默模式，仅显示错误")
    print()


def _print_config_summary(config: Config, config_path: Path) -> None:
    """打印当前配置的简要信息（不含文件详情）。"""
    print()
    print(f"  ╭─ 配置文件 ──────────────────────────────────")
    print(f"  │  {config_path}")
    print(f"  │  可直接编辑此文件来修改仓库或添加文件映射")
    print(f"  ╰" + "─" * 48)
    print()
    print(f"  提交模板: {config.commit_template}")
    print(f"  排除规则: {', '.join(config.exclude)}")
    print(f"\n  ── 已配置 {len(config.repos)} 个仓库 ──")
    for i, repo in enumerate(config.repos, 1):
        remote_str = ", ".join(repo.remotes) if repo.remotes else "(无远程)"
        print(f"  [{i}] {repo.name}")
        print(f"      {repo.path}")
        print(f"      远程: {remote_str}")


def _print_repo_detail(config: Config, repo_name: str) -> None:
    """打印指定仓库的完整信息，包括文件列表。"""
    for repo in config.repos:
        if repo.name == repo_name:
            print()
            print(f"  ╭─ 仓库: {repo.name} ─" + "─" * (34 - len(repo.name)))
            print(f"  │  路径: {repo.path}")
            remote_str = ", ".join(repo.remotes) if repo.remotes else "(无)"
            print(f"  │  远程: {remote_str}")
            if repo.files:
                print(f"  │  同步文件:")
                for f in repo.files:
                    print(f"  │    {f.source}")
                    print(f"  │      → {f.dest}")
            else:
                print(f"  │  同步文件: (无)")
            print(f"  ╰" + "─" * 46)
            return
    print(f"  未找到仓库: {repo_name}")


def _list_repos(config: Config) -> None:
    """列出所有已配置的仓库。"""
    print("\n已配置的仓库：")
    if not config.repos:
        print("  （无）")
        return
    for i, repo in enumerate(config.repos, 1):
        print(f"  {i}. {repo.name}")
        print(f"     {repo.path}")
        remote_str = ", ".join(repo.remotes) if repo.remotes else "(无远程)"
        print(f"     远程: {remote_str}")
    print()


def _push_single_repo(
    config: Config,
    config_path: Path,
    repo_name: str | None = None,
) -> bool:
    """推送单个仓库。

    Args:
        config: 解析后的配置对象。
        config_path: 配置文件路径。
        repo_name: 仓库名称（可选）。如果为 None，显示交互式选择。

    Returns:
        是否成功推送。
    """
    if not config.repos:
        print("  没有已配置的仓库，请先添加仓库。")
        return False

    if repo_name:
        # CLI 模式：按名称查找
        target = next((r for r in config.repos if r.name == repo_name), None)
        if not target:
            print(f"未找到仓库 '{repo_name}'，运行 `gpa list` 查看可用仓库")
            return False
        run_single(target, config_path)
        return True

    # 交互模式：显示列表选择
    print("\n推送指定仓库:\n")
    for i, repo in enumerate(config.repos, 1):
        remote_str = ", ".join(repo.remotes) if repo.remotes else "(无远程)"
        print(f"  {i}. {repo.name}")
        print(f"     {repo.path}")
        print(f"     远程: {remote_str}")
        print()
    print("  0. 返回")

    sel = _input_simple("\n  输入仓库编号: ")
    try:
        idx = int(sel) - 1
        if idx < 0 or idx >= len(config.repos):
            return False
    except (ValueError, IndexError):
        return False

    target = config.repos[idx]
    run_single(target, config_path)
    return True


def _manage_repo_menu(config_path: Path) -> bool:
    """管理仓库子菜单：选择仓库 → 查看详情 → 删除或重配。返回 True 表示配置已变更。"""
    config = parse_config(config_path)
    names = [repo.name for repo in config.repos if repo.name]
    if not names:
        print("  没有已配置的仓库。")
        return False

    print()
    for i, name in enumerate(names, 1):
        print(f"  {i}. {name}")
    print(f"  0. 返回")

    sel = _input_simple("\n  输入仓库编号: ")
    try:
        idx = int(sel) - 1
        if idx < 0 or idx >= len(names):
            return False
    except (ValueError, IndexError):
        return False

    target = names[idx]

    # 展示该仓库的完整信息
    _print_repo_detail(config, target)

    print(f"\n  操作 \"{target}\":")
    print(f"    1. 删除此仓库")
    print(f"    2. 重新配置此仓库")
    print(f"    0. 返回")

    op = _input_simple("\n  输入选项: ")
    if op == "1":
        _clear_screen()
        confirm = _input_simple(f"  确认删除仓库 \"{target}\"？[y/N]: ")
        if confirm.lower() in ("y", "yes"):
            delete_repo_from_config(config_path, target)
            return True
        print("  已取消。")
    elif op == "2":
        _clear_screen()
        reconfigure_repo_in_config(config_path, target)
        return True

    return False


def _input_simple(prompt: str) -> str:
    """简易输入，出错不退出。"""
    try:
        return input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return ""


def _safe_input(prompt: str) -> str:
    """带 KeyboardInterrupt 保护的 input。"""
    try:
        return input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        print("\n")
        raise SystemExit(0)


def _interactive_menu(config_path: Path) -> None:
    """已有配置时的交互式菜单：展示配置，询问用户操作。"""
    config = parse_config(config_path)

    _print_config_summary(config, config_path)

    while True:
        print()
        print(_SEP)
        print(" 操作:")
        print("   1. 执行 Git Push (同步并推送所有仓库)")
        print("   2. 推送指定仓库 (选择单个仓库推送)")
        print("   3. 添加新的 Git 仓库")
        print("   4. 管理已有仓库 (删除 / 重新配置)")
        print("   5. 重新运行配置向导 (覆盖当前配置)")
        print("   6. 退出")
        print(_SEP)

        choice = _safe_input(" 输入选项 [1]: ") or "1"

        if choice == "1":
            print()
            run_all(config, config_path, verbose=False)
            break
        elif choice == "2":
            _clear_screen()
            if _push_single_repo(config, config_path):
                break
            # 如果用户选择返回，重新显示配置摘要
            config = parse_config(config_path)
            _print_config_summary(config, config_path)
        elif choice == "3":
            _clear_screen()
            result = append_repo_to_config(config_path)
            if result == "duplicate:push":
                run_all(config, config_path, verbose=False)
                break
            elif result == "duplicate:manage":
                changed = _manage_repo_menu(config_path)
                if changed:
                    config = parse_config(config_path)
                    _print_config_summary(config, config_path)
                continue
            config = parse_config(config_path)
            _print_config_summary(config, config_path)
        elif choice == "4":
            changed = _manage_repo_menu(config_path)
            if changed:
                config = parse_config(config_path)
                _print_config_summary(config, config_path)
        elif choice == "5":
            _clear_screen()
            run_wizard(config_path)
            config = parse_config(config_path)
            _print_config_summary(config, config_path)
        elif choice == "6":
            print("  退出。")
            break
        else:
            print("  无效选项，请输入 1-6。")


def main() -> None:
    try:
        _main()
    except KeyboardInterrupt:
        print()
        sys.exit(0)


def _main() -> None:
    parser = argparse.ArgumentParser(
        prog="gpa",
        description="Git Push All — 同步 dotfiles 到 Git 仓库并推送到多个远程仓库",
    )
    parser.add_argument(
        "-c", "--config",
        default=None,
        help="配置文件路径（默认: 自动检测已保存的配置）",
    )
    parser.add_argument(
        "action",
        nargs="?",
        default=None,
        help="init: 配置向导, list: 列出仓库, push: 推送指定仓库",
    )
    parser.add_argument(
        "repo_name",
        nargs="?",
        default=None,
        help="仓库名称（用于 'push' 操作）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="仅预览，不实际执行",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="详细输出",
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="静默模式，仅显示错误",
    )

    args = parser.parse_args()

    has_explicit_action = (
        args.action in ("init", "list", "push")
        or args.config is not None
    )

    # ── 有明确命令 → 清屏后执行 ──
    if has_explicit_action:
        _clear_screen()

    # 显式 init — 运行向导，然后进入交互菜单
    if args.action == "init":
        config_path = Path(args.config) if args.config else Path.home() / ".gitpush.toml"
        run_wizard(config_path)
        _interactive_menu(config_path)
        return

    # 显式 list — 列出所有已配置的仓库
    if args.action == "list":
        result = _resolve_config(args.config, save=False)
        if result is None:
            return
        config_path, config = result
        _list_repos(config)
        return

    # 显式 push — 推送指定仓库
    if args.action == "push":
        if not args.repo_name:
            print("请指定仓库名称，例如: gpa push <name>")
            return
        result = _resolve_config(args.config)
        if result is None:
            return
        config_path, config = result
        if not _push_single_repo(config, config_path, args.repo_name):
            sys.exit(1)
        return

    # 显式指定配置文件
    if args.config:
        config_path = Path(args.config)
        if not config_path.exists():
            print(f"未找到配置文件: {config_path}")
            print("运行 'gpa init' 创建配置，或检查路径是否正确。")
            sys.exit(1)
        save_config_path(config_path)
        config = parse_config(config_path)

        if args.dry_run:
            print(f"预览模式 — 将处理 {len(config.repos)} 个仓库:")
            for repo in config.repos:
                print(f"  [{repo.name}] {repo.path} → 远程: {repo.remotes}")
                for f in repo.files:
                    print(f"    复制: {f.source} → {f.dest}")
            return

        run_all(config, config_path, verbose=args.verbose)
        return

    # ── 无参数 → 打印命令说明，然后检测配置 ──
    _print_banner()

    saved_path = load_config_path()

    if saved_path is None:
        print("  未找到已保存的配置。")
        print()
        print("  运行以下命令开始配置:")
        print("    gpa init          创建默认配置 (~/.gitpush.toml)")
        print("    gpa -c <路径>     指定已有配置文件")
        sys.exit(0)

    config_path = Path(saved_path)
    if not config_path.exists():
        print(f"  已保存的配置文件不存在: {config_path}")
        print("  运行 'gpa init' 重新创建配置。")
        sys.exit(0)

    _interactive_menu(config_path)
