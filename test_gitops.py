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
