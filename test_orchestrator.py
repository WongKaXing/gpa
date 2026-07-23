"""测试 orchestrator 模块的单仓库推送功能。"""
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from gitpush.config import RepoConfig
from gitpush.orchestrator import run_single


@pytest.fixture
def repo_config(tmp_path: Path) -> tuple[RepoConfig, Path]:
    """创建测试用的仓库配置和配置文件路径。"""
    repo = RepoConfig(
        name="test-repo",
        path=str(tmp_path / "repo"),
        remotes=["origin"],
        files=[],
        commit_template="update {date}",
    )
    config_path = tmp_path / "config.toml"
    config_path.write_text("[defaults]\ncommit_template = 'update {date}'\n")
    return repo, config_path


def test_run_single_repo(repo_config: tuple[RepoConfig, Path]) -> None:
    """测试 run_single 函数处理单个仓库。"""
    repo, config_path = repo_config

    with patch("gitpush.orchestrator._process_repo") as mock_process:
        mock_result = MagicMock()
        mock_result.status = "ok"
        mock_result.repo_name = "test-repo"
        mock_result.sync_result = None
        mock_result.git_result = None
        mock_result.error_details = []
        mock_process.return_value = mock_result

        result = run_single(repo, config_path)

        # 验证 _process_repo 被调用
        mock_process.assert_called_once()
        call_args = mock_process.call_args
        assert call_args[0][0] == repo
        assert isinstance(call_args[0][1], Path)

        # 验证返回值（空列表表示成功）
        assert result == []


def test_run_single_repo_returns_errors(repo_config: tuple[RepoConfig, Path]) -> None:
    """测试 run_single 函数返回出错的仓库名列表。"""
    repo, config_path = repo_config

    with patch("gitpush.orchestrator._process_repo") as mock_process:
        mock_result = MagicMock()
        mock_result.status = "error"
        mock_result.repo_name = "test-repo"
        mock_result.sync_result = None
        mock_result.git_result = None
        mock_result.error_details = ["推送失败"]
        mock_process.return_value = mock_result

        result = run_single(repo, config_path)

        # 验证返回值包含出错的仓库名
        assert "test-repo" in result
