"""交互式配置向导 — 首次运行时生成 gitpush.toml，也支持追加/删除/重配仓库。"""
from __future__ import annotations

import os as _os
import re as _re
import subprocess
from pathlib import Path


def _setup_path_completion() -> None:
    """为 input() 启用 Tab 路径自动补全（不区分大小写）。"""
    try:
        import readline
    except ImportError:
        return

    home = _os.path.expanduser("~")

    def _completer(text: str, state: int) -> str | None:
        line = readline.get_line_buffer()
        if not line:
            return None
        expanded = _os.path.expanduser(line)
        dirname = _os.path.dirname(expanded) or "."
        basename = _os.path.basename(expanded)

        try:
            entries = _os.listdir(dirname)
        except OSError:
            return None

        # 大小写不敏感前缀匹配
        lower_base = basename.lower()
        matches = [
            _os.path.join(dirname, e)
            for e in entries
            if e.lower().startswith(lower_base)
        ]

        dirs = sorted(m + _os.sep for m in matches if _os.path.isdir(m))
        files = sorted(m + " " for m in matches if _os.path.isfile(m))
        results = dirs + files

        # 保持原始 ~ 表示
        if line.startswith("~"):
            results = [r.replace(home, "~", 1) for r in results]

        try:
            return results[state]
        except IndexError:
            return None

    # 分隔符只保留 tab 和换行，确保路径不被拆分
    readline.set_completer_delims("\t\n")
    readline.set_completer(_completer)

    if "libedit" in readline.__doc__:
        readline.parse_and_bind("bind ^I rl_complete")
    else:
        readline.parse_and_bind("tab: complete")


def _input(prompt: str) -> str:
    """安全输入封装，优雅处理 EOF/KeyboardInterrupt。"""
    try:
        return input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        print("\n已取消。")
        raise SystemExit(0)


def _scan_directory(path: str) -> list[str]:
    """列出目录中的所有条目。"""
    p = Path(path).expanduser().resolve()
    if not p.exists() or not p.is_dir():
        print(f"  目录未找到: {p}")
        return []
    entries = sorted(
        [e.name for e in p.iterdir()],
        key=str.lower,
    )
    return entries


def _select_items(entries: list[str]) -> list[str]:
    """显示编号列表，返回用户选择的项目名称。"""
    for i, name in enumerate(entries, 1):
        print(f"  {i}. {name}")

    choice = _input(f"选择要同步的项目（逗号分隔数字，或输入 'all' 全选）: ")
    if choice.lower() == "all":
        return entries

    selected: list[str] = []
    for part in choice.split(","):
        part = part.strip()
        try:
            idx = int(part) - 1
            if 0 <= idx < len(entries):
                if entries[idx] not in selected:
                    selected.append(entries[idx])
        except ValueError:
            matching = [e for e in entries if e.lower() == part.lower()]
            for m in matching:
                if m not in selected:
                    selected.append(m)

    return selected


def _detect_remotes(repo_path: str) -> dict[str, str | None]:
    """运行 git remote -v，返回 {远程仓库名: fetch_url} 字典。"""
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
    """如果 remote_name 存在则直接返回，否则提示用户添加。"""
    remotes = _detect_remotes(repo_path)
    if remote_name in remotes:
        print(f"  检测到已有的远程仓库: {remote_name} → {remotes[remote_name]}")
        return remote_name

    url = _input(f"  未找到 {remote_name} 远程仓库，输入 URL（输入 'None' 跳过）: ")
    if url.lower() == "none" or not url:
        return None

    p = Path(repo_path).expanduser().resolve()
    subprocess.run(
        ["git", "remote", "add", remote_name, url],
        cwd=p, capture_output=True,
    )
    print(f"  已添加远程仓库: {remote_name} → {url}")
    return remote_name


def _build_repo_section(repo_count: int) -> tuple[list[str], str, str] | None:
    """交互式构建一个仓库配置段，返回 (TOML行列表, 名称, 路径) 或 None。"""
    print(f"\n── 仓库 #{repo_count} ──")

    source = _input("输入要扫描的源目录（例如 ~/.config，或输入 'None' 跳过复制）: ")
    selected: list[str] = []
    source_path = ""

    is_single_file = False
    if source.lower() != "none" and source:
        source_path = source
        src_expanded = Path(source).expanduser()
        if src_expanded.is_file():
            is_single_file = True
            selected = [str(src_expanded)]
            print(f"  已选择文件: {src_expanded}")
        else:
            entries = _scan_directory(source)
            if entries:
                selected = _select_items(entries)
                print(f"  已选择: {', '.join(selected)}")
                modify = _input("  修改选择？[y/N]: ")
                if modify.lower() in ("y", "yes"):
                    selected = _select_items(entries)
                    print(f"  更新后的选择: {', '.join(selected)}")
            else:
                print("  目录中未找到任何条目。")

    upload = _input("输入要同步到的 Git 仓库目录: ")
    if not upload:
        print("  跳过 — 未提供仓库路径。")
        return None

    remotes: list[str] = []
    for name in ("gitee", "github"):
        r = _configure_remote(upload, name)
        if r:
            remotes.append(r)

    name = Path(upload).expanduser().name
    lines: list[str] = []
    lines.append("[[repos]]")
    lines.append(f'name = "{name}"')
    lines.append(f'path = "{upload}"')
    remotes_toml = ", ".join(f'"{r}"' for r in remotes)
    lines.append(f"remotes = [{remotes_toml}]")
    lines.append("")

    for item in selected:
        if is_single_file:
            item_source = item
        else:
            item_source = str(Path(source_path).expanduser() / item)
        lines.append("[[repos.files]]")
        lines.append(f'source = "{item_source}"')
        lines.append(f'dest = "."')
        lines.append("")

    return lines, name, str(Path(upload).expanduser().resolve())


# ── TOML 文本操作 ────────────────────────────────────────────


def _get_existing_repo_info(config_path: Path) -> list[tuple[str, str]]:
    """返回已有仓库的 (名称, 已解析路径) 列表。"""
    if not config_path.exists():
        return []
    text = config_path.read_text()
    # 匹配 [[repos]] name = "..." path = "..."
    pattern = r'\[\[repos\]\]\nname = "(.+?)"\npath = "(.+?)"'
    result = []
    for m in _re.finditer(pattern, text):
        name = m.group(1)
        path_str = m.group(2)
        resolved = str(Path(path_str).expanduser().resolve())
        result.append((name, resolved))
    return result


def _find_duplicate(config_path: Path, new_name: str, new_path: str) -> tuple[str, str] | None:
    """检查新仓库是否与已有仓库重复，返回已有的 (名称, 路径) 或 None。"""
    existing = _get_existing_repo_info(config_path)
    resolved_new = str(Path(new_path).expanduser().resolve())
    for name, path in existing:
        if name == new_name or path == resolved_new:
            return (name, path)
    return None


def _handle_duplicate(config_path: Path, name: str, path: str) -> str | None:
    """重复仓库提示，返回用户选择: 'push' / 'manage' / None(取消)。"""
    from gitpush.config import parse_config
    config = parse_config(config_path)

    print(f"\n  ⚠ 仓库已存在!")
    print(f"  名称: {name}")
    print(f"  路径: {path}")
    print(f"\n  该仓库已在配置中，无需重复添加。")
    print(f"\n  你可以:")
    print(f"    1. 返回主菜单执行推送")
    print(f"    2. 管理已有仓库")
    print(f"    0. 取消")

    choice = _input("\n  输入选项 [0]: ") or "0"
    if choice == "1":
        return "push"
    elif choice == "2":
        return "manage"
    return None


def _list_repo_names(config_path: Path) -> list[str]:
    """从 TOML 文件中提取所有仓库名称。"""
    import re
    text = config_path.read_text()
    return re.findall(r'^\[\[repos\]\]\nname = "(.+)"', text, re.MULTILINE)


def _delete_repo_from_toml(text: str, repo_name: str) -> str:
    """从 TOML 文本中删除指定仓库的 [[repos]] 段及其 [[repos.files]]。"""
    lines = text.splitlines()
    result: list[str] = []
    skipping = False
    i = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # 检测 [[repos]] 段头（排除 [[repos.files]]）
        if stripped.startswith("[[repos]]") and not stripped.startswith("[[repos.files]]"):
            if i + 1 < len(lines) and f'name = "{repo_name}"' in lines[i + 1]:
                skipping = True
                i += 1
                continue
            else:
                skipping = False

        if skipping:
            # 遇到下一个 [[repos]] 或顶级 section 时停止跳过
            if stripped.startswith("[[repos]]") and not stripped.startswith("[[repos.files]]"):
                skipping = False
                result.append(line)
            elif stripped.startswith("[") and not stripped.startswith("[["):
                skipping = False
                result.append(line)
            # 否则：跳过此行
        else:
            result.append(line)

        i += 1

    return "\n".join(result).rstrip() + "\n"


def delete_repo_from_config(config_path: str | Path, repo_name: str) -> bool:
    """从配置文件中删除指定仓库，返回是否成功。"""
    config_path = Path(config_path)
    text = config_path.read_text()
    if f'name = "{repo_name}"' not in text:
        print(f"  未找到仓库: {repo_name}")
        return False
    new_text = _delete_repo_from_toml(text, repo_name)
    config_path.write_text(new_text)
    print(f"  已删除仓库: {repo_name}")
    return True


def reconfigure_repo_in_config(config_path: str | Path, repo_name: str) -> None:
    """删除旧配置，然后交互式重建同一个仓库。"""
    _setup_path_completion()
    config_path = Path(config_path)
    text = config_path.read_text()

    if f'name = "{repo_name}"' not in text:
        print(f"  未找到仓库: {repo_name}")
        return

    text = _delete_repo_from_toml(text, repo_name)

    print(f"\n重新配置仓库: {repo_name}")
    result = _build_repo_section(1)
    if not result:
        print("已取消，仓库配置未更改（旧配置已删除，请手动恢复）。")
        return

    section_lines, _, _ = result
    if not text.endswith("\n"):
        text += "\n"
    config_path.write_text(text + "\n".join(section_lines) + "\n")
    print(f"\n 仓库 {repo_name} 已更新")


# ── 主入口 ────────────────────────────────────────────────────


def run_wizard(config_path: str | Path = "gitpush.toml") -> None:
    """运行交互式配置并写入 gitpush.toml。"""
    _setup_path_completion()
    config_path = Path(config_path)

    print("╭──────────────────────────────────────────────╮")
    print("│        GPA — 交互式配置向导                  │")
    print("╰──────────────────────────────────────────────╯\n")

    commit_template = _input(
        "提交信息模板？（默认: 'update {date}'）: "
    )
    if not commit_template:
        commit_template = "update {date}"

    exclude_input = _input(
        "排除的 glob 匹配模式？（默认: .DS_Store, __pycache__, *.pyc）: "
    )
    if not exclude_input:
        exclude = [".DS_Store", "__pycache__", "*.pyc"]
    else:
        exclude = [p.strip() for p in exclude_input.split(",") if p.strip()]

    lines: list[str] = []
    lines.append("[defaults]")
    lines.append(f'commit_template = "{commit_template}"')
    exclude_toml = ", ".join(f'"{e}"' for e in exclude)
    lines.append(f"exclude = [{exclude_toml}]")
    lines.append("")

    repo_count = 0
    session_paths: set[str] = set()  # 本次会话已添加的路径
    while True:
        repo_count += 1
        result = _build_repo_section(repo_count)
        if result:
            section_lines, name, path = result
            # 检查与会话内已添加的仓库是否重复
            if path in session_paths:
                _handle_duplicate(config_path, name, path)
                repo_count -= 1
                continue
            session_paths.add(path)
            lines.extend(section_lines)

        again = _input("\n添加另一个仓库？[y/N]: ")
        if again.lower() not in ("y", "yes"):
            break

    config_path.write_text("\n".join(lines) + "\n")
    print(f"\n 配置已写入 {config_path.resolve()}")

    from gitpush.state import save_config_path
    save_config_path(config_path)


def append_repo_to_config(config_path: str | Path) -> str:
    """向已有配置文件追加一个新的仓库配置（检测重复）。

    返回:
      'added' — 成功添加
      'cancelled' — 用户取消
      'duplicate:push' — 检测到重复，用户选择推送
      'duplicate:manage' — 检测到重复，用户选择管理仓库
    """
    _setup_path_completion()
    config_path = Path(config_path)
    existing = config_path.read_text()

    repo_count = existing.count("[[repos]]")

    result = _build_repo_section(repo_count + 1)
    if not result:
        print("已取消，未添加任何仓库。")
        return "cancelled"

    section_lines, name, path = result

    # 检测重复
    dup = _find_duplicate(config_path, name, path)
    if dup:
        action = _handle_duplicate(config_path, name, path)
        if action == "push":
            return "duplicate:push"
        elif action == "manage":
            return "duplicate:manage"
        return "cancelled"

    if not existing.endswith("\n"):
        existing += "\n"

    config_path.write_text(existing + "\n".join(section_lines) + "\n")
    print(f"\n 仓库已追加到 {config_path.resolve()}")
    return "added"
