"""测试 CLI 模块功能，包括仓库列表、单仓库推送和 CLI 命令。"""
from pathlib import Path
from unittest.mock import patch

from gitpush.cli import _list_repos, _push_single_repo, _get_config_path
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
    assert "已配置的仓库" in captured.out
    assert "1. local-repo" in captured.out
    assert "~/Documents/Git/local" in captured.out
    assert "远程: (无远程)" in captured.out


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
        mock_run.assert_called_once_with(config.repos[0], config_path)


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
