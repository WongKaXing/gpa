# 单仓库推送功能实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 GPA 添加单仓库推送功能，支持通过交互菜单或 CLI 命令推送指定仓库

**Architecture:** 在现有架构基础上，添加 `run_single()` 函数处理单仓库推送，修改 CLI 添加 `push` 和 `list` 子命令，在交互菜单中添加 "推送指定仓库" 选项

**Tech Stack:** Python 3.12+, 标准库 (argparse, pathlib, tomllib)

---

## 文件结构

### 修改文件
- `gitpush/cli.py` — 添加 `list` 和 `push` 子命令，添加交互菜单选项
- `gitpush/orchestrator.py` — 添加 `run_single()` 函数

### 测试文件
- `tests/test_cli.py` — 测试 CLI 命令
- `tests/test_orchestrator.py` — 测试单仓库推送

---

## Task 1: 添加 run_single() 函数

**Files:**
- Modify: `gitpush/orchestrator.py`
- Test: `tests/test_orchestrator.py`

- [ ] **Step 1: 编写失败测试**

```python
# tests/test_orchestrator.py
"""测试 orchestrator 模块的单仓库推送功能。"""
from pathlib import Path
from unittest.mock import patch, MagicMock

from gitpush.config import RepoConfig
from gitpush.orchestrator import run_single


def test_run_single_repo(tmp_path: Path) -> None:
    """测试 run_single 函数处理单个仓库。"""
    # 准备测试仓库配置
    repo = RepoConfig(
        name="test-repo",
        path=str(tmp_path / "repo"),
        remotes=["origin"],
        files=[],
        commit_template="update {date}",
    )
    config_path = tmp_path / "config.toml"
    config_path.write_text("[defaults]\ncommit_template = 'update {date}'\n")

    # Mock _process_repo 函数
    with patch("gitpush.orchestrator._process_repo") as mock_process:
        mock_result = MagicMock()
        mock_result.status = "ok"
        mock_process.return_value = mock_result

        # 调用 run_single
        run_single(repo, config_path)

        # 验证 _process_repo 被调用
        mock_process.assert_called_once()
        call_args = mock_process.call_args
        assert call_args[0][0] == repo
        assert isinstance(call_args[0][1], Path)


def test_run_single_repo_prints_summary(tmp_path: Path, capsys) -> None:
    """测试 run_single 函数打印汇总信息。"""
    repo = RepoConfig(
        name="test-repo",
        path=str(tmp_path / "repo"),
        remotes=["origin"],
        files=[],
        commit_template="update {date}",
    )
    config_path = tmp_path / "config.toml"
    config_path.write_text("[defaults]\ncommit_template = 'update {date}'\n")

    with patch("gitpush.orchestrator._process_repo") as mock_process:
        mock_result = MagicMock()
        mock_result.status = "ok"
        mock_result.repo_name = "test-repo"
        mock_result.sync_result = None
        mock_result.git_result = None
        mock_result.error_details = []
        mock_process.return_value = mock_result

        run_single(repo, config_path)

        # 验证输出包含开始推送信息
        captured = capsys.readouterr()
        assert "开始推送 test-repo" in captured.out
```

- [ ] **Step 2: 运行测试验证失败**

```bash
cd /Users/soc/Documents/PyDemo/gpa
python -m pytest tests/test_orchestrator.py -v
```

预期输出：FAIL — `ImportError: cannot import name 'run_single' from 'gitpush.orchestrator'`

- [ ] **Step 3: 编写最小实现**

```python
# gitpush/orchestrator.py — 在文件末尾添加

def run_single(repo: RepoConfig, config_path: str | Path) -> None:
    """运行单个仓库的同步和推送。

    Args:
        repo: 要推送的仓库配置。
        config_path: 配置文件路径（用于确定配置目录）。
    """
    config_dir = Path(config_path).resolve().parent
    print(f"\n开始推送 {repo.name}...")
    result = _process_repo(repo, config_dir)
    print_summary([result])
```

- [ ] **Step 4: 运行测试验证通过**

```bash
cd /Users/soc/Documents/PyDemo/gpa
python -m pytest tests/test_orchestrator.py -v
```

预期输出：PASSED

- [ ] **Step 5: 提交代码**

```bash
git add gitpush/orchestrator.py tests/test_orchestrator.py
git commit -m "feat: 添加 run_single() 函数支持单仓库推送"
```

---

## Task 2: 添加 _list_repos() 函数

**Files:**
- Modify: `gitpush/cli.py`

- [ ] **Step 1: 编写失败测试**

```python
# tests/test_cli.py
"""测试 CLI 模块的仓库列表功能。"""
from pathlib import Path
from unittest.mock import patch

from gitpush.cli import _list_repos
from gitpush.config import Config, RepoConfig


def test_list_repos(capsys) -> None:
    """测试 _list_repos 函数输出仓库列表。"""
    config = Config(
        repos=[
            RepoConfig(
                name="nvim",
                path="~/Documents/Git/nvim",
                remotes=["gitee", "github"],
            ),
            RepoConfig(
                name="dotfiles",
                path="~/Documents/Git/dotfiles",
                remotes=["github"],
            ),
        ]
    )

    _list_repos(config)

    captured = capsys.readouterr()
    assert "已配置的仓库" in captured.out
    assert "1. nvim" in captured.out
    assert "~/Documents/Git/nvim" in captured.out
    assert "远程: gitee, github" in captured.out
    assert "2. dotfiles" in captured.out
    assert "~/Documents/Git/dotfiles" in captured.out
    assert "远程: github" in captured.out


def test_list_repos_empty(capsys) -> None:
    """测试 _list_repos 函数处理空仓库列表。"""
    config = Config(repos=[])

    _list_repos(config)

    captured = capsys.readouterr()
    assert "已配置的仓库" in captured.out
    assert "（无）" in captured.out
```

- [ ] **Step 2: 运行测试验证失败**

```bash
cd /Users/soc/Documents/PyDemo/gpa
python -m pytest tests/test_cli.py::test_list_repos -v
```

预期输出：FAIL — `ImportError: cannot import name '_list_repos' from 'gitpush.cli'`

- [ ] **Step 3: 编写最小实现**

```python
# gitpush/cli.py — 在 _print_repo_detail 函数后添加

def _list_repos(config: Config) -> None:
    """列出所有已配置的仓库。"""
    print("\n已配置的仓库：")
    if not config.repos:
        print("  （无）")
        return
    for i, repo in enumerate(config.repos, 1):
        print(f"  {i}. {repo.name}")
        print(f"     {repo.path}")
        if repo.remotes:
            print(f"     远程: {', '.join(repo.remotes)}")
    print()
```

- [ ] **Step 4: 运行测试验证通过**

```bash
cd /Users/soc/Documents/PyDemo/gpa
python -m pytest tests/test_cli.py::test_list_repos -v
```

预期输出：PASSED

- [ ] **Step 5: 提交代码**

```bash
git add gitpush/cli.py tests/test_cli.py
git commit -m "feat: 添加 _list_repos() 函数列出所有仓库"
```

---

## Task 3: 添加 _push_single_repo() 函数

**Files:**
- Modify: `gitpush/cli.py`
- Test: `tests/test_cli.py`

- [ ] **Step 1: 编写失败测试**

```python
# tests/test_cli.py — 继续添加

def test_push_single_repo_by_name(capsys) -> None:
    """测试 _push_single_repo 函数按名称推送。"""
    config = Config(
        repos=[
            RepoConfig(
                name="nvim",
                path="~/Documents/Git/nvim",
                remotes=["gitee", "github"],
            ),
        ]
    )
    config_path = Path("/tmp/config.toml")

    with patch("gitpush.cli.run_single") as mock_run:
        result = _push_single_repo(config, config_path, "nvim")
        assert result is True
        mock_run.assert_called_once()


def test_push_single_repo_not_found(capsys) -> None:
    """测试 _push_single_repo 函数处理不存在的仓库。"""
    config = Config(
        repos=[
            RepoConfig(
                name="nvim",
                path="~/Documents/Git/nvim",
                remotes=["gitee", "github"],
            ),
        ]
    )
    config_path = Path("/tmp/config.toml")

    result = _push_single_repo(config, config_path, "nonexistent")
    assert result is False

    captured = capsys.readouterr()
    assert "未找到仓库 'nonexistent'" in captured.out


def test_push_single_repo_empty_config(capsys) -> None:
    """测试 _push_single_repo 函数处理空配置。"""
    config = Config(repos=[])
    config_path = Path("/tmp/config.toml")

    result = _push_single_repo(config, config_path)
    assert result is False

    captured = capsys.readouterr()
    assert "没有已配置的仓库" in captured.out


def test_push_single_repo_interactive(capsys) -> None:
    """测试 _push_single_repo 函数交互式选择。"""
    config = Config(
        repos=[
            RepoConfig(
                name="nvim",
                path="~/Documents/Git/nvim",
                remotes=["gitee", "github"],
            ),
            RepoConfig(
                name="dotfiles",
                path="~/Documents/Git/dotfiles",
                remotes=["github"],
            ),
        ]
    )
    config_path = Path("/tmp/config.toml")

    with patch("gitpush.cli.run_single") as mock_run, \
         patch("gitpush.cli._input_simple", return_value="1"):
        result = _push_single_repo(config, config_path)
        assert result is True
        mock_run.assert_called_once()
```

- [ ] **Step 2: 运行测试验证失败**

```bash
cd /Users/soc/Documents/PyDemo/gpa
python -m pytest tests/test_cli.py::test_push_single_repo_by_name -v
```

预期输出：FAIL — `ImportError: cannot import name '_push_single_repo' from 'gitpush.cli'`

- [ ] **Step 3: 编写最小实现**

```python
# gitpush/cli.py — 在 _list_repos 函数后添加

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
```

- [ ] **Step 4: 运行测试验证通过**

```bash
cd /Users/soc/Documents/PyDemo/gpa
python -m pytest tests/test_cli.py -v
```

预期输出：PASSED

- [ ] **Step 5: 提交代码**

```bash
git add gitpush/cli.py tests/test_cli.py
git commit -m "feat: 添加 _push_single_repo() 函数支持单仓库推送"
```

---

## Task 4: 修改交互菜单添加推送指定仓库选项

**Files:**
- Modify: `gitpush/cli.py`
- Test: `tests/test_cli.py`

- [ ] **Step 1: 编写失败测试**

```python
# tests/test_cli.py — 继续添加

def test_interactive_menu_push_single(capsys) -> None:
    """测试交互菜单中的推送指定仓库选项。"""
    from gitpush.cli import _interactive_menu

    config_path = Path("/tmp/config.toml")
    config_path.write_text("""
[defaults]
commit_template = "update {date}"

[[repos]]
name = "nvim"
path = "~/Documents/Git/nvim"
remotes = ["gitee", "github"]
""")

    # 模拟用户选择 "2" (推送指定仓库)，然后 "1" (选择第一个仓库)，然后 "5" (退出)
    with patch("gitpush.cli._safe_input", side_effect=["2", "1", "5"]), \
         patch("gitpush.cli.run_single") as mock_run, \
         patch("gitpush.cli._clear_screen"):
        _interactive_menu(config_path)
        mock_run.assert_called_once()
```

- [ ] **Step 2: 运行测试验证失败**

```bash
cd /Users/soc/Documents/PyDemo/gpa
python -m pytest tests/test_cli.py::test_interactive_menu_push_single -v
```

预期输出：FAIL — 测试失败，因为菜单中没有 "2" 选项

- [ ] **Step 3: 修改交互菜单**

```python
# gitpush/cli.py — 修改 _interactive_menu 函数

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
```

- [ ] **Step 4: 运行测试验证通过**

```bash
cd /Users/soc/Documents/PyDemo/gpa
python -m pytest tests/test_cli.py -v
```

预期输出：PASSED

- [ ] **Step 5: 提交代码**

```bash
git add gitpush/cli.py tests/test_cli.py
git commit -m "feat: 修改交互菜单添加推送指定仓库选项"
```

---

## Task 5: 添加 CLI 子命令

**Files:**
- Modify: `gitpush/cli.py`
- Test: `tests/test_cli.py`

- [ ] **Step 1: 编写失败测试**

```python
# tests/test_cli.py — 继续添加

def test_cli_list_command(capsys) -> None:
    """测试 gpa list 命令。"""
    from gitpush.cli import main

    config_path = Path("/tmp/config.toml")
    config_path.write_text("""
[defaults]
commit_template = "update {date}"

[[repos]]
name = "nvim"
path = "~/Documents/Git/nvim"
remotes = ["gitee", "github"]
""")

    with patch("sys.argv", ["gpa", "list", "-c", str(config_path)]):
        main()

    captured = capsys.readouterr()
    assert "已配置的仓库" in captured.out
    assert "1. nvim" in captured.out


def test_cli_push_command(capsys) -> None:
    """测试 gpa push <name> 命令。"""
    from gitpush.cli import main

    config_path = Path("/tmp/config.toml")
    config_path.write_text("""
[defaults]
commit_template = "update {date}"

[[repos]]
name = "nvim"
path = "~/Documents/Git/nvim"
remotes = ["gitee", "github"]
""")

    with patch("sys.argv", ["gpa", "push", "nvim", "-c", str(config_path)]), \
         patch("gitpush.cli.run_single") as mock_run:
        main()
        mock_run.assert_called_once()


def test_cli_push_command_not_found(capsys) -> None:
    """测试 gpa push <name> 命令处理不存在的仓库。"""
    from gitpush.cli import main

    config_path = Path("/tmp/config.toml")
    config_path.write_text("""
[defaults]
commit_template = "update {date}"

[[repos]]
name = "nvim"
path = "~/Documents/Git/nvim"
remotes = ["gitee", "github"]
""")

    with patch("sys.argv", ["gpa", "push", "nonexistent", "-c", str(config_path)]):
        main()

    captured = capsys.readouterr()
    assert "未找到仓库 'nonexistent'" in captured.out
```

- [ ] **Step 2: 运行测试验证失败**

```bash
cd /Users/soc/Documents/PyDemo/gpa
python -m pytest tests/test_cli.py::test_cli_list_command -v
```

预期输出：FAIL — 测试失败，因为 `list` 子命令未定义

- [ ] **Step 3: 修改 CLI 解析器**

```python
# gitpush/cli.py — 修改 _main 函数

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
        help="输入 'init' 运行配置向导，'list' 列出仓库，'push <name>' 推送指定仓库",
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

    # 显式 list — 列出所有仓库
    if args.action == "list":
        config_path = Path(args.config) if args.config else _get_config_path()
        if not config_path:
            return
        config = parse_config(config_path)
        _list_repos(config)
        return

    # 显式 push — 推送指定仓库
    if args.action == "push":
        if not args.repo_name:
            print("错误: 请指定仓库名称，例如: gpa push nvim")
            sys.exit(1)
        config_path = Path(args.config) if args.config else _get_config_path()
        if not config_path:
            return
        config = parse_config(config_path)
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
```

- [ ] **Step 4: 运行测试验证通过**

```bash
cd /Users/soc/Documents/PyDemo/gpa
python -m pytest tests/test_cli.py -v
```

预期输出：PASSED

- [ ] **Step 5: 提交代码**

```bash
git add gitpush/cli.py tests/test_cli.py
git commit -m "feat: 添加 list 和 push CLI 子命令"
```

---

## Task 6: 更新文档

**Files:**
- Modify: `README.md`

- [ ] **Step 1: 更新 README.md**

```markdown
# GPA — Git Push All

一键同步 dotfiles / 配置文件到 Git 仓库，并推送到多个远程仓库。

## 安装

```bash
# 克隆项目
git clone git@github.com:WongKaXing/gpa.git
cd gpa

# 使用 uv 安装为系统命令
uv tool install .
```

安装完成后，直接在终端使用 `gpa` 命令。

**依赖**：Python ≥ 3.12，纯标准库，无外部依赖。

## 快速开始

```bash
gpa init    # 首次运行，交互式配置向导
gpa         # 后续运行，进入交互菜单
gpa -c ~/gitpush.toml   # 直接执行推送
gpa list    # 列出所有已配置的仓库
gpa push nvim   # 推送指定仓库
```

## 配置文件

默认配置文件位于 `~/gitpush.toml`，格式如下：

```toml
[defaults]
commit_template = "update {date}"     # 提交信息模板 {date} 会被替换为当前日期
exclude = [".DS_Store", "__pycache__", "*.pyc"]  # 全局排除规则

[[repos]]
name = "nvim"                         # 仓库名称
path = "~/Documents/Git/nvim/"        # Git 仓库本地路径
remotes = ["gitee", "github"]         # 远程仓库名列表

[[repos.files]]
source = "~/.config/nvim"             # 源文件/目录
dest = "."                            # 目标相对路径（相对于仓库根目录）

[[repos.files]]
source = "/path/to/single/file"       # 也支持单个文件
dest = "subdir"                       # 复制到仓库的子目录
```

## 交互菜单

`gpa` 无参数运行时会显示 banner 和交互菜单：

```
1. 执行 Git Push — 同步并推送所有仓库
2. 推送指定仓库 — 选择单个仓库推送
3. 添加新的 Git 仓库 — 进入向导添加仓库
4. 管理已有仓库 — 查看详情 / 删除 / 重新配置
5. 重新运行配置向导 — 覆盖当前配置
6. 退出
```

添加仓库时支持 Tab 路径自动补全，自动检测重复仓库。

## 命令行参数

| 参数 | 说明 |
|------|------|
| `gpa init` | 运行交互式配置向导 |
| `gpa list` | 列出所有已配置的仓库 |
| `gpa push <name>` | 推送指定仓库 |
| `gpa -c <路径>` | 指定配置文件直接推送 |
| `gpa --dry-run` | 预览模式，仅显示将要执行的操作 |
| `gpa -v, --verbose` | 详细输出 |
| `gpa -q, --quiet` | 静默模式，仅显示错误 |

## 工作流程

1. **文件同步** — 将配置文件中指定的源文件/目录复制到对应 Git 仓库
2. **Git 提交** — 按提交模板自动 `git add -A` 并 `git commit`
3. **推送远程** — 依次 `git push` 到配置的所有远程仓库

## 状态持久化

工具会记住上次使用的配置文件路径，存储在 `~/.config/gitpush/state.json`。首次使用后，直接运行 `gpa` 即可自动找到配置。
```

- [ ] **Step 2: 提交代码**

```bash
git add README.md
git commit -m "docs: 更新 README 添加 list 和 push 命令说明"
```

---

## Task 7: 运行完整测试套件

- [ ] **Step 1: 运行所有测试**

```bash
cd /Users/soc/Documents/PyDemo/gpa
python -m pytest tests/ -v
```

预期输出：所有测试 PASSED

- [ ] **Step 2: 检查测试覆盖率**

```bash
cd /Users/soc/Documents/PyDemo/gpa
python -m pytest tests/ --cov=gitpush --cov-report=term-missing
```

预期输出：覆盖率报告，确保新增代码有足够测试覆盖

- [ ] **Step 3: 提交最终代码**

```bash
git add -A
git commit -m "feat: 完成单仓库推送功能实现"
```

---

## 总结

本计划实现了 GPA 的单仓库推送功能，包括：

1. **run_single() 函数** — 处理单个仓库的同步和推送
2. **_list_repos() 函数** — 列出所有已配置的仓库
3. **_push_single_repo() 函数** — 支持按名称或交互式选择推送单个仓库
4. **交互菜单更新** — 添加 "推送指定仓库" 选项
5. **CLI 子命令** — 添加 `list` 和 `push` 命令
6. **文档更新** — 更新 README 说明新功能

所有代码都遵循 TDD 原则，先写测试再实现，确保代码质量。