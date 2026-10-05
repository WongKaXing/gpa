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


def test_pushes_pending_commit_without_new_changes(tmp_path):
    """回归：已提交但未推送的提交，即使这次没有新改动也要推上去。"""
    repo = tmp_path / "local"
    repo.mkdir()
    _init_repo(repo)

    bare = tmp_path / "bare.git"
    bare.mkdir()
    _init_bare_repo(bare)
    subprocess.run(
        ["git", "remote", "add", "origin", str(bare)], cwd=repo, capture_output=True
    )

    # 模拟「上次推送失败，留下未推的提交」：只提交，不推送
    (repo / "pending.txt").write_text("pending")
    subprocess.run(["git", "add", "-A"], cwd=repo, capture_output=True)
    subprocess.run(["git", "commit", "-m", "pending"], cwd=repo, capture_output=True)

    result = git_sync(repo, remotes=["origin"], commit_template="update {date}")

    assert result.committed is False  # 这次没有新改动
    assert result.pushed is True  # 但把未推的提交推出去了
    assert result.push_ok == ["origin"]
    assert result.push_fail == []
    log = subprocess.run(
        ["git", "log", "--oneline"], cwd=bare, capture_output=True, text=True
    ).stdout
    assert "pending" in log


def test_up_to_date_repo_is_not_pushed_again(tmp_path):
    """没有新改动、也没有未推提交时，不该再推一次（保持「无变更」快速路径）。"""
    repo = tmp_path / "local"
    repo.mkdir()
    _init_repo(repo)

    bare = tmp_path / "bare.git"
    bare.mkdir()
    _init_bare_repo(bare)
    subprocess.run(
        ["git", "remote", "add", "origin", str(bare)], cwd=repo, capture_output=True
    )

    (repo / "new.txt").write_text("first")
    first = git_sync(repo, remotes=["origin"], commit_template="update {date}")
    assert first.pushed is True

    second = git_sync(repo, remotes=["origin"], commit_template="update {date}")
    assert second.committed is False
    assert second.pushed is False
    assert second.push_ok == []


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


def test_message_overrides_template(tmp_path):
    """-m 传入的提交信息应覆盖 commit_template。"""
    repo = tmp_path / "local"
    repo.mkdir()
    _init_repo(repo)
    (repo / "new.txt").write_text("changed")

    result = git_sync(repo, remotes=[], commit_template="update {date}", message="fix: 手写信息")

    assert result.committed is True
    assert result.commit_message == "fix: 手写信息"
    log = subprocess.run(
        ["git", "log", "-1", "--pretty=%s"], cwd=repo, capture_output=True, text=True
    ).stdout.strip()
    assert log == "fix: 手写信息"


def test_message_supports_date_placeholder(tmp_path):
    """-m 里的 {date} 仍会被替换为当天日期。"""
    repo = tmp_path / "local"
    repo.mkdir()
    _init_repo(repo)
    (repo / "new.txt").write_text("changed")

    result = git_sync(repo, remotes=[], commit_template="update {date}", message="chore: 备份 {date}")

    assert result.commit_message == f"chore: 备份 {date.today().isoformat()}"


def test_blank_message_falls_back_to_template(tmp_path):
    """-m 传空白字符串时回退到 commit_template，不产生空提交信息。"""
    repo = tmp_path / "local"
    repo.mkdir()
    _init_repo(repo)
    (repo / "new.txt").write_text("changed")

    result = git_sync(repo, remotes=[], commit_template="update {date}", message="   ")

    assert result.commit_message == f"update {date.today().isoformat()}"


def test_message_keeps_unknown_braces(tmp_path):
    """提交信息里的其它花括号应原样保留，不触发 KeyError。"""
    repo = tmp_path / "local"
    repo.mkdir()
    _init_repo(repo)
    (repo / "new.txt").write_text("changed")

    result = git_sync(repo, remotes=[], commit_template="update {date}", message="fix: 处理 {config} 解析")

    assert result.committed is True
    assert result.commit_message == "fix: 处理 {config} 解析"
