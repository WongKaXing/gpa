"""测试 CLI 模块功能，包括仓库列表、单仓库推送和 CLI 命令。"""
from pathlib import Path
from unittest.mock import patch

from gitpush.cli import _list_repos, _push_single_repo, _get_config_path
from gitpush.config import Config, RepoConfig


def test_list_repos(capsys) -> None:
    """测试 _list_repos 函数输出仓库列表（按名称字母排序）。"""
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
    assert "已配置 2 个仓库" in captured.out
    # 默认按名称字母排序：dotfiles 在前；不显示路径
    assert "[1]  dotfiles" in captured.out
    assert "github" in captured.out
    assert "[2]  nvim" in captured.out
    assert "gitee, github" in captured.out
    assert "~/Documents/Git/" not in captured.out


def test_list_repos_empty(capsys) -> None:
    """测试 _list_repos 函数处理空仓库列表。"""
    config = Config(repos=[])

    _list_repos(config)

    captured = capsys.readouterr()
    assert "已配置 0 个仓库" in captured.out


def test_list_repos_no_remotes(capsys) -> None:
    """测试 _list_repos 函数处理没有远程仓库的情况。"""
    config = Config(
        repos=[
            RepoConfig(
                name="local-repo",
                path="~/Documents/Git/local",
                remotes=[],
            ),
        ]
    )

    _list_repos(config)

    captured = capsys.readouterr()
    assert "已配置 1 个仓库" in captured.out
    assert "[1]  local-repo" in captured.out
    assert "(无远程)" in captured.out
    assert "~/Documents/Git/local" not in captured.out


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
    """测试 _push_single_repo 函数交互式选择（默认按名称字母排序，选 1 为 dotfiles）。"""
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
        # 排序后 [1] = dotfiles（原 config.repos[1]）
        mock_run.assert_called_once_with(config.repos[1], config_path)


def test_push_single_repo_interactive_invalid_input(capsys) -> None:
    """测试 _push_single_repo 函数交互式选择输入非数字。"""
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

    with patch("gitpush.cli._input_simple", return_value="abc"):
        result = _push_single_repo(config, config_path)
        assert result is False


def test_push_single_repo_interactive_out_of_range(capsys) -> None:
    """测试 _push_single_repo 函数交互式选择输入越界编号。"""
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

    with patch("gitpush.cli._input_simple", return_value="99"):
        result = _push_single_repo(config, config_path)
        assert result is False


def test_push_single_repo_interactive_return(capsys) -> None:
    """测试 _push_single_repo 函数交互式选择返回操作。"""
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

    with patch("gitpush.cli._input_simple", return_value="0"):
        result = _push_single_repo(config, config_path)
        assert result is False


def test_get_config_path_no_saved_config(fake_home, capsys) -> None:
    """测试 _get_config_path 函数处理没有保存的配置。"""

    with patch("gitpush.cli.load_config_path", return_value=None):
        result = _get_config_path()
        assert result is None

    captured = capsys.readouterr()
    assert "未找到已保存的配置" in captured.out


def test_get_config_path_config_not_exist(fake_home, capsys) -> None:
    """测试 _get_config_path 函数处理配置文件不存在。"""

    nonexistent_path = fake_home.parent / "nonexistent.toml"
    with patch("gitpush.cli.load_config_path", return_value=str(nonexistent_path)):
        result = _get_config_path()
        assert result is None

    captured = capsys.readouterr()
    assert "注意: 已保存的配置文件已不存在" in captured.out
    assert "未找到已保存的配置" in captured.out


def test_cli_push_no_repo_name(capsys) -> None:
    """测试 gpa push 命令没有指定仓库名称。"""
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

    with patch("sys.argv", ["gpa", "push", "-c", str(config_path)]):
        main()

    captured = capsys.readouterr()
    assert "请指定仓库名称" in captured.out


def test_cli_list_no_config(fake_home, capsys) -> None:
    """测试 gpa list 命令没有配置文件。"""
    from gitpush.cli import main

    with patch("sys.argv", ["gpa", "list"]), \
         patch("gitpush.cli.load_config_path", return_value=None):
        main()

    captured = capsys.readouterr()
    assert "未找到已保存的配置" in captured.out


def test_cli_push_no_config(fake_home, capsys) -> None:
    """测试 gpa push 命令没有配置文件。"""
    from gitpush.cli import main

    with patch("sys.argv", ["gpa", "push", "nvim"]), \
         patch("gitpush.cli.load_config_path", return_value=None):
        main()

    captured = capsys.readouterr()
    assert "未找到已保存的配置" in captured.out


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

    # 模拟用户选择 "2" (推送指定仓库)，然后 "1" (选择第一个仓库)，然后 "6" (退出)
    with patch("gitpush.cli._safe_input", side_effect=["2", "6"]), \
         patch("gitpush.cli._input_simple", return_value="1") as mock_input, \
         patch("gitpush.cli.run_single") as mock_run, \
         patch("gitpush.cli._clear_screen"):
        _interactive_menu(config_path)
        mock_run.assert_called_once()


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
    assert "已配置 1 个仓库" in captured.out
    assert "[1]  nvim" in captured.out


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
    import pytest
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

    with pytest.raises(SystemExit) as exc_info:
        with patch("sys.argv", ["gpa", "push", "nonexistent", "-c", str(config_path)]):
            main()
    assert exc_info.value.code == 1

    captured = capsys.readouterr()
    assert "未找到仓库 'nonexistent'" in captured.out


def test_get_config_path_fallback_to_default(fake_home) -> None:
    """当 state 路径失效但 ~/.gitpush.toml 存在时，自动回退注册。"""
    from gitpush.cli import _get_config_path

    default_config = fake_home / ".gitpush.toml"
    default_config.write_text("")

    # state 里有旧路径但不存在
    nonexistent = str(fake_home.parent / "nonexistent.toml")
    with patch("gitpush.cli.load_config_path", return_value=nonexistent):
        with patch("gitpush.cli.save_config_path") as mock_save:
            result = _get_config_path()

    assert result == default_config
    mock_save.assert_called_once_with(default_config)


def test_get_config_path_no_state_default_exists(fake_home) -> None:
    """当无 state 但 ~/.gitpush.toml 存在时，自动注册。"""
    from gitpush.cli import _get_config_path

    default_config = fake_home / ".gitpush.toml"
    default_config.write_text("")

    with patch("gitpush.cli.load_config_path", return_value=None):
        with patch("gitpush.cli.save_config_path") as mock_save:
            result = _get_config_path()

    assert result == default_config
    mock_save.assert_called_once_with(default_config)


def test_get_config_path_no_state_no_default(fake_home, capsys) -> None:
    """当无 state 且 ~/.gitpush.toml 也不存在时，返回 None。"""
    from gitpush.cli import _get_config_path

    with patch("gitpush.cli.load_config_path", return_value=None):
        result = _get_config_path()

    assert result is None
    captured = capsys.readouterr()
    assert "未找到已保存的配置" in captured.out


def test_interactive_menu_quit_with_q(capsys) -> None:
    """测试交互菜单输入 q 直接退出程序。"""
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

    with patch("gitpush.cli._safe_input", return_value="q"):
        _interactive_menu(config_path)

    captured = capsys.readouterr()
    assert "退出" in captured.out


def test_push_single_repo_interactive_quit(capsys) -> None:
    """测试 _push_single_repo 交互选择时输入 q 返回主菜单。"""
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

    with patch("gitpush.cli._input_simple", return_value="q"):
        result = _push_single_repo(config, config_path)
    assert result is False


def test_manage_repo_menu_quit(capsys) -> None:
    """测试管理仓库菜单输入 q 返回主菜单。"""
    from gitpush.cli import _manage_repo_menu

    config_path = Path("/tmp/config.toml")
    config_path.write_text("""
[defaults]
commit_template = "update {date}"

[[repos]]
name = "nvim"
path = "~/Documents/Git/nvim"
remotes = ["gitee", "github"]
""")

    with patch("gitpush.cli._input_simple", return_value="q"):
        result = _manage_repo_menu(config_path)
    assert result is False


def test_manage_repo_menu_op_quit_returns_to_selection(capsys) -> None:
    """测试操作菜单按 q 返回仓库选择列表（上一个模块），再按 q 返回主菜单。"""
    from gitpush.cli import _manage_repo_menu

    config_path = Path("/tmp/config.toml")
    config_path.write_text("""
[defaults]
commit_template = "update {date}"

[[repos]]
name = "nvim"
path = "~/Documents/Git/nvim"
remotes = ["gitee", "github"]
""")

    # 第 1 次: 选择仓库 "1"；第 2 次: 操作菜单按 q 返回列表；第 3 次: 列表按 q 返回主菜单
    with patch("gitpush.cli._input_simple", side_effect=["1", "q", "q"]) as mock_input:
        result = _manage_repo_menu(config_path)
    assert result is False
    assert mock_input.call_count == 3


def test_cli_all_command(capsys) -> None:
    """测试 gpa -a 命令直接推送所有仓库。"""
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

    with patch("sys.argv", ["gpa", "-a", "-c", str(config_path)]), \
         patch("gitpush.cli.run_all") as mock_run:
        main()
        mock_run.assert_called_once()


def test_cli_all_auto_detect_config(fake_home) -> None:
    """测试 gpa -a 无 -c 时自动使用默认配置文件，无需用户指定。"""
    from gitpush.cli import main

    default_config = fake_home / ".gitpush.toml"
    default_config.write_text("""
[defaults]
commit_template = "update {date}"

[[repos]]
name = "nvim"
path = "~/Documents/Git/nvim"
remotes = ["gitee", "github"]
""")

    with patch("sys.argv", ["gpa", "-a"]), \
         patch("gitpush.cli.load_config_path", return_value=None), \
         patch("gitpush.cli.run_all") as mock_run:
        main()
        mock_run.assert_called_once()


def test_cli_all_dry_run(capsys) -> None:
    """测试 gpa -a --dry-run 只预览不执行。"""
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

    with patch("sys.argv", ["gpa", "-a", "--dry-run", "-c", str(config_path)]), \
         patch("gitpush.cli.run_all") as mock_run:
        main()
        mock_run.assert_not_called()

    captured = capsys.readouterr()
    assert "预览模式" in captured.out


def test_cli_version(capsys) -> None:
    """测试 gpa -v 显示版本信息。"""
    import pytest
    from gitpush import __version__
    from gitpush.cli import main

    with pytest.raises(SystemExit) as exc_info:
        with patch("sys.argv", ["gpa", "-v"]):
            main()
    assert exc_info.value.code == 0

    captured = capsys.readouterr()
    assert "gpa" in captured.out
    assert __version__ in captured.out


def test_cli_config_override_does_not_save_state(capsys) -> None:
    """测试 -c 一次性覆盖不写入状态文件，避免覆盖已记住的配置。"""
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

    with patch("sys.argv", ["gpa", "-a", "-c", str(config_path)]), \
         patch("gitpush.cli.run_all"), \
         patch("gitpush.cli.save_config_path") as mock_save:
        main()
        mock_save.assert_not_called()


def test_interactive_menu_manage_clears_screen(capsys) -> None:
    """测试选 4 管理仓库前清屏，返回首页后也清屏重绘，避免输出堆积。"""
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

    with patch("gitpush.cli._safe_input", side_effect=["4", "q"]), \
         patch("gitpush.cli._input_simple", return_value="q"), \
         patch("gitpush.cli._clear_screen") as mock_clear:
        _interactive_menu(config_path)

    # 进入 4 前清一次 + 返回首页重绘清一次
    assert mock_clear.call_count == 2


def test_repo_table_sorted_alphabetically(capsys) -> None:
    """测试仓库列表默认按名称字母排序（不区分大小写）。"""
    from gitpush.cli import _print_repo_table

    config = Config(
        repos=[
            RepoConfig(name="zsh", path="~/z", remotes=["github"]),
            RepoConfig(name="alpha", path="~/a", remotes=["github"]),
            RepoConfig(name="Beta", path="~/b", remotes=["github"]),
        ]
    )

    _print_repo_table(config)

    captured = capsys.readouterr()
    # 排序后顺序: alpha → Beta → zsh
    assert captured.out.index("alpha") < captured.out.index("Beta")
    assert captured.out.index("Beta") < captured.out.index("zsh")


def test_push_single_repo_by_index(capsys) -> None:
    """测试 gpa push 支持序号（按排序后 1-based 序号）。"""
    from gitpush.cli import main

    config_path = Path("/tmp/config.toml")
    config_path.write_text("""
[defaults]
commit_template = "update {date}"

[[repos]]
name = "nvim"
path = "~/Documents/Git/nvim"
remotes = ["gitee", "github"]

[[repos]]
name = "alpha"
path = "~/Documents/Git/alpha"
remotes = ["github"]
""")

    with patch("sys.argv", ["gpa", "push", "1", "-c", str(config_path)]), \
         patch("gitpush.cli.run_single") as mock_run:
        main()
        # 排序后 [1] = alpha
        mock_run.assert_called_once()
        assert mock_run.call_args[0][0].name == "alpha"


def test_push_single_repo_by_custom_name_case_insensitive(capsys) -> None:
    """测试 gpa push 支持自定义仓库名（不区分大小写）。"""
    from gitpush.cli import main

    config_path = Path("/tmp/config.toml")
    config_path.write_text("""
[defaults]
commit_template = "update {date}"

[[repos]]
name = "我的Nvim配置"
path = "~/Documents/Git/nvim"
remotes = ["gitee", "github"]
""")

    with patch("sys.argv", ["gpa", "push", "我的nvim配置", "-c", str(config_path)]), \
         patch("gitpush.cli.run_single") as mock_run:
        main()
        mock_run.assert_called_once()
        assert mock_run.call_args[0][0].name == "我的Nvim配置"


def test_push_single_repo_index_out_of_range(capsys) -> None:
    """测试 gpa push 序号越界返回失败。"""
    import pytest
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

    with pytest.raises(SystemExit) as exc_info:
        with patch("sys.argv", ["gpa", "push", "9", "-c", str(config_path)]):
            main()
    assert exc_info.value.code == 1


def test_settings_show_usage_false(_isolate_settings, capsys, fake_home) -> None:
    """测试设置 show_usage=false 时无参数运行不显示用法 banner。"""
    from gitpush.cli import main

    _isolate_settings.write_text("show_usage = false\n")

    default_config = fake_home / ".gitpush.toml"
    default_config.write_text("""
[defaults]
commit_template = "update {date}"
[[repos]]
name = "nvim"
path = "~/Documents/Git/nvim"
remotes = ["gitee", "github"]
""")

    with patch("sys.argv", ["gpa"]), \
         patch("gitpush.cli.load_config_path", return_value=None), \
         patch("gitpush.cli._interactive_menu") as mock_menu:
        main()
        mock_menu.assert_called_once()

    captured = capsys.readouterr()
    assert "用法:" not in captured.out
    assert "GPA — Git Push All" not in captured.out


def test_settings_default_action_push(_isolate_settings, capsys, fake_home) -> None:
    """测试设置 default_action=push 时无参数直接推送全部仓库。"""
    from gitpush.cli import main

    _isolate_settings.write_text('default_action = "push"\nshow_usage = false\n')

    default_config = fake_home / ".gitpush.toml"
    default_config.write_text("""
[defaults]
commit_template = "update {date}"
[[repos]]
name = "nvim"
path = "~/Documents/Git/nvim"
remotes = ["gitee", "github"]
""")

    with patch("sys.argv", ["gpa"]), \
         patch("gitpush.cli.load_config_path", return_value=None), \
         patch("gitpush.cli.run_all") as mock_run:
        main()
        mock_run.assert_called_once()


def test_repo_table_desc_order(_isolate_settings, capsys) -> None:
    """测试 sort_order=desc 时仓库列表倒序显示。"""
    from gitpush.cli import _print_repo_table
    from gitpush.config import Config
    from gitpush.settings import Settings

    config = Config(
        repos=[
            RepoConfig(name="zsh", path="~/z", remotes=["github"]),
            RepoConfig(name="alpha", path="~/a", remotes=["github"]),
        ]
    )

    with patch("gitpush.cli._SETTINGS", Settings(sort_order="desc")):
        _print_repo_table(config)

    captured = capsys.readouterr()
    assert captured.out.index("zsh") < captured.out.index("alpha")
