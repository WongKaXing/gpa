"""测试向导模块的 q 取消行为（q = 返回上一个模块位置）。"""
from unittest.mock import patch

from gitpush.wizard import (
    append_repo_to_config,
    reconfigure_repo_in_config,
    run_wizard,
)

CONFIG_TEXT = """\
[defaults]
commit_template = "update {date}"

[[repos]]
name = "nvim"
path = "~/Documents/Git/nvim"
remotes = ["gitee", "github"]
"""


def test_run_wizard_q_cancels(tmp_path) -> None:
    """向导中按 q 取消，不写入配置文件。"""
    config_path = tmp_path / "gitpush.toml"

    with patch("builtins.input", return_value="q"):
        result = run_wizard(config_path)

    assert result is False
    assert not config_path.exists()


def test_run_wizard_uppercase_q_cancels(tmp_path) -> None:
    """向导中按大写 Q 同样取消。"""
    config_path = tmp_path / "gitpush.toml"

    with patch("builtins.input", return_value="Q"):
        result = run_wizard(config_path)

    assert result is False
    assert not config_path.exists()


def test_append_repo_q_cancels(tmp_path) -> None:
    """追加仓库时按 q 取消，配置不变。"""
    config_path = tmp_path / "gitpush.toml"
    config_path.write_text(CONFIG_TEXT)

    with patch("builtins.input", return_value="q"):
        result = append_repo_to_config(config_path)

    assert result == "cancelled"
    assert config_path.read_text() == CONFIG_TEXT


def test_reconfigure_repo_q_restores(tmp_path) -> None:
    """重新配置仓库时按 q 取消，恢复原配置。"""
    config_path = tmp_path / "gitpush.toml"
    config_path.write_text(CONFIG_TEXT)

    with patch("builtins.input", return_value="q"):
        reconfigure_repo_in_config(config_path, "nvim")

    assert config_path.read_text() == CONFIG_TEXT
