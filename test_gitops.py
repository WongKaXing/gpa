"""Tests for git operations."""
import tempfile
import subprocess
from pathlib import Path
from datetime import date
from gitpush.gitops import git_sync, _fill_template, _has_staged_changes


def _init_repo(path: Path) -> None:
    subprocess.run(["git", "init"], cwd=path, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=path, capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=path, capture_output=True,
    )
    # Create an initial commit so there's a branch to push from
    (path / "initial.txt").write_text("init")
    subprocess.run(["git", "add", "-A"], cwd=path, capture_output=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=path, capture_output=True)


def _init_bare_repo(path: Path) -> None:
    subprocess.run(["git", "init", "--bare", str(path)], capture_output=True)


def test_fill_template():
    result = _fill_template("update {date}")
    assert date.today().isoformat() in result


def test_fill_template_custom():
    result = _fill_template("backup {date}")
    assert result.startswith("backup ")


def test_no_changes_no_commit():
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        _init_repo(repo)
        result = git_sync(repo, remotes=[], commit_template="update {date}")
        assert result.committed is False


def test_commit_when_changes():
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        _init_repo(repo)
        (repo / "new.txt").write_text("changed")
        result = git_sync(repo, remotes=[], commit_template="update {date}")
        assert result.committed is True


def test_push_to_remote():
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp) / "local"
        repo.mkdir()
        _init_repo(repo)

        bare = Path(tmp) / "bare.git"
        bare.mkdir()
        _init_bare_repo(bare)

        subprocess.run(
            ["git", "remote", "add", "origin", str(bare)],
            cwd=repo, capture_output=True,
        )

        (repo / "new.txt").write_text("push me")
        result = git_sync(repo, remotes=["origin"], commit_template="update {date}")
        assert result.committed is True
        assert "origin" in result.push_ok
        assert len(result.push_fail) == 0


def test_push_missing_remote():
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp)
        _init_repo(repo)
        (repo / "new.txt").write_text("test")
        result = git_sync(repo, remotes=["nonexistent"], commit_template="update {date}")
        assert len(result.push_fail) == 1
        assert result.push_fail[0][0] == "nonexistent"


def test_ensure_git_repo_initializes_new(tmp_path):
    """测试新目录自动 git init + 添加远程 + 切分支。"""
    from gitpush.gitops import ensure_git_repo

    repo_dir = tmp_path / "newrepo"
    msgs = ensure_git_repo(
        repo_dir,
        remotes=["gitee", "github"],
        remote_urls={
            "gitee": "git@gitee.com:user/newrepo.git",
            "github": "git@github.com:user/newrepo.git",
        },
        branch="main",
    )

    assert (repo_dir / ".git").exists()
    remotes = __import__("subprocess").run(
        ["git", "remote"], cwd=repo_dir, capture_output=True, text=True
    ).stdout.splitlines()
    assert "gitee" in remotes and "github" in remotes
    branch = __import__("subprocess").run(
        ["git", "branch", "--show-current"], cwd=repo_dir, capture_output=True, text=True
    ).stdout.strip()
    assert branch == "main"
    assert any("已初始化" in m for m in msgs)
    assert any("已添加远程" in m for m in msgs)


def test_ensure_git_repo_updates_existing_remote(tmp_path):
    """测试已有仓库远程 URL 不匹配时自动 set-url。"""
    import subprocess
    from gitpush.gitops import ensure_git_repo

    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    subprocess.run(["git", "init", "-b", "main"], cwd=repo_dir, capture_output=True)
    subprocess.run(
        ["git", "remote", "add", "gitee", "git@gitee.com:old/old.git"],
        cwd=repo_dir, capture_output=True,
    )

    msgs = ensure_git_repo(
        repo_dir,
        remotes=["gitee"],
        remote_urls={"gitee": "git@gitee.com:user/new.git"},
        branch="main",
    )

    url = subprocess.run(
        ["git", "remote", "get-url", "gitee"], cwd=repo_dir, capture_output=True, text=True
    ).stdout.strip()
    assert url == "git@gitee.com:user/new.git"
    assert any("URL 已更新" in m for m in msgs)


def test_ensure_git_repo_missing_url_hint(tmp_path):
    """测试只有远程名没有 URL 时给出补充提示（不报错）。"""
    from gitpush.gitops import ensure_git_repo

    repo_dir = tmp_path / "repo"
    msgs = ensure_git_repo(repo_dir, remotes=["gitee"], remote_urls={}, branch="main")

    assert (repo_dir / ".git").exists()
    assert any("未配置 URL" in m for m in msgs)
