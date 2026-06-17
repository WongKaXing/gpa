"""gpa 命令的 CLI 入口。"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from gitpush.config import parse_config, Config
from gitpush.orchestrator import run_all
from gitpush.state import load_config_path, save_config_path
from gitpush.wizard import (
    run_wizard, append_repo_to_config,
    delete_repo_from_config, reconfigure_repo_in_config,
    _list_repo_names,
)

_SEP = "─" * 48
_THIN = "╌" * 48


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
    print(f"    默认位置: ~/gitpush.toml")
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


def _manage_repo_menu(config_path: Path) -> bool:
    """管理仓库子菜单：选择仓库 → 查看详情 → 删除或重配。返回 True 表示配置已变更。"""
    config = parse_config(config_path)
    names = _list_repo_names(config_path)
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
        print("   2. 添加新的 Git 仓库")
        print("   3. 管理已有仓库 (删除 / 重新配置)")
        print("   4. 重新运行配置向导 (覆盖当前配置)")
        print("   5. 退出")
        print(_SEP)

        choice = _safe_input(" 输入选项 [1]: ") or "1"

        if choice == "1":
            print()
            run_all(config, config_path, verbose=False)
            break
        elif choice == "2":
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
        elif choice == "3":
            changed = _manage_repo_menu(config_path)
            if changed:
                config = parse_config(config_path)
                _print_config_summary(config, config_path)
        elif choice == "4":
            _clear_screen()
            run_wizard(config_path)
            config = parse_config(config_path)
            _print_config_summary(config, config_path)
        elif choice == "5":
            print("  退出。")
            break
        else:
            print("  无效选项，请输入 1-5。")


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
        help="输入 'init' 运行配置向导",
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
        args.action == "init"
        or args.config is not None
    )

    # ── 有明确命令 → 清屏后执行 ──
    if has_explicit_action:
        _clear_screen()

    # 显式 init — 运行向导，然后进入交互菜单
    if args.action == "init":
        config_path = Path(args.config) if args.config else Path("gitpush.toml")
        run_wizard(config_path)
        _interactive_menu(config_path)
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
        print("    gpa init          创建默认配置 (~/gitpush.toml)")
        print("    gpa -c <路径>     指定已有配置文件")
        sys.exit(0)

    config_path = Path(saved_path)
    if not config_path.exists():
        print(f"  已保存的配置文件不存在: {config_path}")
        print("  运行 'gpa init' 重新创建配置。")
        sys.exit(0)

    _interactive_menu(config_path)
