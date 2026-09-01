"""gpa 命令的 CLI 入口。"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from gitpush import __version__ as _VERSION
from gitpush.config import parse_config, Config, RepoConfig
from gitpush.orchestrator import run_all, run_single
from gitpush.state import load_config_path, save_config_path
from gitpush.utils import center, color, display_width, pad_to
from gitpush.wizard import (
    run_wizard, append_repo_to_config,
    delete_repo_from_config, reconfigure_repo_in_config,
)

_CYAN = "36"
_GREEN = "32"
_YELLOW = "33"
_RED = "31"
_BOLD = "1"
_BOX_W = 50


def _box_row(text: str) -> str:
    """生成右侧边框对齐的框内行（按显示宽度补位）。"""
    return "  " + color("│", _CYAN) + " " + pad_to(text, _BOX_W - 2) + " " + color("│", _CYAN)


def _box_top(title: str = "") -> str:
    """生成框顶行（可选标题居中）。"""
    if title:
        inner = center(f" {title} ", _BOX_W - 2)
        return "  " + color("╭─", _CYAN) + pad_to(inner, _BOX_W - 2) + color("─╮", _CYAN)
    return "  " + color("╭", _CYAN) + "─" * _BOX_W + color("╮", _CYAN)


def _box_bottom() -> str:
    return "  " + color("╰", _CYAN) + "─" * _BOX_W + color("╯", _CYAN)


def _get_config_path() -> Path | None:
    """获取配置文件路径。先查 state 快取，失效则回退到 ~/.gitpush.toml 并自动注册。"""
    saved_path = load_config_path()
    if saved_path is not None:
        config_path = Path(saved_path)
        if config_path.exists():
            return config_path
        # saved path is stale — inform user, then try default
        print(f"注意: 已保存的配置文件已不存在 ({config_path})，正在检查默认路径...")
    # 回退：检查默认路径
    default_config = Path.home() / ".gitpush.toml"
    if default_config.exists():
        save_config_path(default_config)
        return default_config
    # 两者都没有
    print("未找到已保存的配置。")
    print("运行 'gpa init' 创建配置，或使用 -c 参数指定配置文件。")
    return None


def _resolve_config(config_arg: str | None) -> tuple[Path, Config] | None:
    """解析配置文件路径并加载配置。

    Args:
        config_arg: -c 参数指定的配置文件路径，可能为 None。

    Returns:
        (config_path, config) 元组，或 None 表示失败。

    说明:
        - 显式 -c 属于一次性覆盖，不会写入状态文件，避免覆盖系统已记住的配置。
        - 未指定 -c 时自动检测（状态文件 → 默认 ~/.gitpush.toml），发现默认路径会自动注册。
    """
    if config_arg:
        config_path = Path(config_arg)
        if not config_path.exists():
            print(f"未找到配置文件: {config_path}")
            print("运行 'gpa init' 创建配置，或检查路径是否正确。")
            return None
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
    print("  " + color("╭", _CYAN) + "─" * _BOX_W + color("╮", _CYAN))
    print("  " + color("│", _CYAN) + " " + center("GPA — Git Push All", _BOX_W - 2) + " " + color("│", _CYAN))
    print("  " + color("│", _CYAN) + " " + center("同步文件到 Git 仓库并推送到多个远程仓库", _BOX_W - 2) + " " + color("│", _CYAN))
    print("  " + color("╰", _CYAN) + "─" * _BOX_W + color("╯", _CYAN))
    print()
    print("  用法:")
    print("    gpa              检测已有配置，进入交互菜单")
    print("    gpa init         首次运行，创建配置文件")
    print("    gpa -a           直接推送所有仓库（自动使用已保存的配置）")
    print("    gpa -c <路径>    指定配置文件直接执行推送")
    print()
    print("  配置文件:")
    print(f"    默认位置: ~/.gitpush.toml")
    print(f"    状态文件: ~/.config/gitpush/state.json")
    print(f"    可直接编辑 TOML 文件来修改仓库配置")
    print()
    print("  可选参数:")
    print("    -v, --version    显示版本信息")
    print("    --dry-run        仅预览，不实际执行")
    print("    --verbose        详细输出每个仓库的处理过程")
    print("    -q, --quiet      静默模式，仅显示错误")
    print()
    print("  提示:")
    print("    交互菜单中按 q 可退出程序，子菜单中按 q 返回上一级")
    print()


def _sorted_repos(config: Config) -> list[RepoConfig]:
    """按仓库名称字母顺序（不区分大小写）排序的仓库列表，作为默认显示顺序。"""
    return sorted(config.repos, key=lambda r: r.name.lower())


def _print_repo_table(config: Config) -> None:
    """打印仓库列表（首页摘要与 gpa list 共用格式，不显示路径）。

    ── 已配置 N 个仓库 ──
      [1]  name   remotes
    """
    repos = _sorted_repos(config)
    print(f"  {color('── 已配置 ' + str(len(repos)) + ' 个仓库 ──', _BOLD)}")
    if not repos:
        return
    max_name = max(display_width(r.name) for r in repos)
    for i, repo in enumerate(repos, 1):
        idx = f"[{i}]".ljust(4)  # [1]..[10] 的 ] 与名称列对齐
        name_col = pad_to(repo.name, max_name)
        remote_str = ", ".join(repo.remotes) if repo.remotes else "(无远程)"
        print(f"  {idx} {name_col}  {color(remote_str, _CYAN)}")


def _print_config_summary(config: Config, config_path: Path) -> None:
    """打印当前配置的简要信息（不含文件详情）。"""
    print()
    print(_box_top("配置文件"))
    print(_box_row(f"{config_path}"))
    print(_box_row("可直接编辑此文件来修改仓库或添加文件映射"))
    print(_box_bottom())
    print()
    print(f"  提交模板: {color(config.commit_template, _GREEN)}")
    print(f"  排除规则: {', '.join(config.exclude)}")
    print()
    _print_repo_table(config)
    print()


def _print_repo_detail(config: Config, repo_name: str) -> None:
    """打印指定仓库的完整信息，包括文件列表。"""
    for repo in config.repos:
        if repo.name == repo_name:
            print()
            print(_box_top(f"仓库: {repo.name}"))
            print(_box_row(f"路径: {repo.path}"))
            remote_str = ", ".join(repo.remotes) if repo.remotes else "(无)"
            print(_box_row(f"远程: {remote_str}"))
            if repo.files:
                print(_box_row(f"同步文件 ({len(repo.files)}):"))
                for f in repo.files:
                    print(_box_row(f"  {f.source}"))
                    print(_box_row(f"  → {f.dest}"))
            else:
                print(_box_row("同步文件: (无)"))
            print(_box_bottom())
            return
    print(f"  未找到仓库: {repo_name}")


def _list_repos(config: Config) -> None:
    """列出所有已配置的仓库（与首页摘要同格式）。"""
    print()
    _print_repo_table(config)
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

    # 交互模式：显示列表选择（按名称字母顺序，不显示路径）
    repos = _sorted_repos(config)
    max_name = max(display_width(r.name) for r in repos)
    print()
    print(_box_top("推送指定仓库"))
    for i, repo in enumerate(repos, 1):
        remote_str = ", ".join(repo.remotes) if repo.remotes else "(无远程)"
        name_col = pad_to(repo.name, max_name)
        print(_box_row(f"[{i}]".ljust(4) + " " + name_col + "  " + remote_str))
    print(_box_row("─" * (_BOX_W - 2)))
    print(_box_row("0. 返回（q）"))
    print(_box_bottom())
    print()

    sel = _input_simple(" 输入仓库编号: ")
    if _is_quit(sel):
        return False
    try:
        idx = int(sel) - 1
        if idx < 0 or idx >= len(repos):
            return False
    except (ValueError, IndexError):
        return False

    target = repos[idx]
    run_single(target, config_path)
    return True


def _manage_repo_menu(config_path: Path) -> bool:
    """管理仓库子菜单：选择仓库 → 查看详情 → 删除或重配。返回 True 表示配置已变更。"""
    while True:
        config = parse_config(config_path)
        names = [repo.name for repo in _sorted_repos(config) if repo.name]
        if not names:
            print("  没有已配置的仓库。")
            return False

        print()
        print(_box_top("管理已有仓库"))
        for i, name in enumerate(names, 1):
            print(_box_row(f"[{i}]".ljust(4) + " " + name))
        print(_box_row("─" * (_BOX_W - 2)))
        print(_box_row("0. 返回（q）"))
        print(_box_bottom())
        print()

        sel = _input_simple(" 输入仓库编号: ")
        if _is_quit(sel):
            return False
        try:
            idx = int(sel) - 1
            if idx < 0 or idx >= len(names):
                return False
        except (ValueError, IndexError):
            return False

        target = names[idx]

        # 展示该仓库的完整信息
        _print_repo_detail(config, target)

        print()
        print(_box_top(f"操作: {target}"))
        print(_box_row("1. 删除此仓库"))
        print(_box_row("2. 重新配置此仓库"))
        print(_box_row("─" * (_BOX_W - 2)))
        print(_box_row("0. 返回（q）"))
        print(_box_bottom())
        print()

        op = _input_simple(" 输入选项: ")
        if _is_quit(op) or op == "0":
            continue  # 返回上一个模块：仓库选择列表
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


def _input_simple(prompt: str) -> str:
    """简易输入，出错不退出。"""
    try:
        return input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return ""


def _is_quit(value: str) -> bool:
    """判断输入是否为退出/返回指令（q 或 Q）。"""
    return value.strip().lower() == "q"


def _safe_input(prompt: str) -> str:
    """带 KeyboardInterrupt 保护的 input。"""
    try:
        return input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        print("\n")
        raise SystemExit(0)


def _interactive_menu(config_path: Path) -> None:
    """已有配置时的交互式菜单：展示配置，询问用户操作。

    每次回到首页先清屏再重绘，进入 2/4 等子功能前也清屏，
    避免旧的输出堆积导致仓库列表看起来重复显示。
    """
    config = parse_config(config_path)

    first = True
    while True:
        if first:
            first = False
        else:
            _clear_screen()
        _print_config_summary(config, config_path)

        print()
        print(_box_top("操作"))
        print(_box_row("1. 执行 Git Push (同步并推送所有仓库)"))
        print(_box_row("2. 推送指定仓库 (选择单个仓库推送)"))
        print(_box_row("3. 添加新的 Git 仓库"))
        print(_box_row("4. 管理已有仓库 (删除 / 重新配置)"))
        print(_box_row("5. 重新运行配置向导 (覆盖当前配置)"))
        print(_box_row("─" * (_BOX_W - 2)))
        print(_box_row("q. 退出"))
        print(_box_bottom())
        print()

        choice = _safe_input(" 输入选项: ") or "1"

        if choice == "1":
            _clear_screen()
            print()
            run_all(config, config_path, verbose=False)
            break
        elif choice == "2":
            _clear_screen()
            if _push_single_repo(config, config_path):
                break
            # 返回主菜单（下一次循环会清屏重绘）
            config = parse_config(config_path)
        elif choice == "3":
            _clear_screen()
            result = append_repo_to_config(config_path)
            if result == "duplicate:push":
                run_all(config, config_path, verbose=False)
                break
            elif result == "duplicate:manage":
                if _manage_repo_menu(config_path):
                    config = parse_config(config_path)
                continue
            config = parse_config(config_path)
        elif choice == "4":
            _clear_screen()
            if _manage_repo_menu(config_path):
                config = parse_config(config_path)
        elif choice == "5":
            _clear_screen()
            if run_wizard(config_path):
                config = parse_config(config_path)
        elif _is_quit(choice):
            print("  退出。")
            break
        else:
            print(color("  无效选项，请输入 1-5，或按 q 退出。", _YELLOW))


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
        "-a", "--all",
        action="store_true",
        help="直接推送所有仓库（自动使用已保存的配置文件）",
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
        "--verbose",
        action="store_true",
        help="详细输出",
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="静默模式，仅显示错误",
    )
    parser.add_argument(
        "-v", "--version",
        action="version",
        version=f"%(prog)s {_VERSION} — Git Push All",
        help="显示版本信息",
    )

    args = parser.parse_args()

    has_explicit_action = (
        args.action in ("init", "list", "push")
        or args.config is not None
        or args.all
    )

    # ── 有明确命令 → 清屏后执行 ──
    if has_explicit_action:
        _clear_screen()

    # 显式 init — 运行向导，然后进入交互菜单
    if args.action == "init":
        config_path = Path(args.config) if args.config else Path.home() / ".gitpush.toml"
        if run_wizard(config_path):
            _interactive_menu(config_path)
        return

    # 显式 list — 列出所有已配置的仓库
    if args.action == "list":
        result = _resolve_config(args.config)
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

    # 显式 -a（推送全部）或 -c（指定配置）→ 直接执行推送，跳过交互菜单
    # 配置文件路径由系统自动记忆（state 文件/默认路径），-c 仅作为覆盖手段
    if args.all or args.config:
        result = _resolve_config(args.config)
        if result is None:
            sys.exit(1)
        config_path, config = result

        if args.dry_run:
            print(f"预览模式 — 将处理 {len(config.repos)} 个仓库:")
            for repo in _sorted_repos(config):
                print(f"  [{repo.name}] {repo.path} → 远程: {repo.remotes}")
                for f in repo.files:
                    print(f"    复制: {f.source} → {f.dest}")
            return

        run_all(config, config_path, verbose=args.verbose)
        return

    # ── 无参数 → 打印命令说明，然后检测配置 ──
    _print_banner()

    config_path = _get_config_path()
    if config_path is None:
        sys.exit(0)

    _interactive_menu(config_path)
