"""Tests for file sync with exclusion."""
import tempfile
from pathlib import Path
from gitpush.config import RepoConfig, FileEntry
from gitpush.filesync import sync_files, _should_exclude


def test_should_exclude_by_name():
    assert _should_exclude(Path("/tmp/.DS_Store"), [".DS_Store"]) is True
    assert _should_exclude(Path("/tmp/real.txt"), [".DS_Store"]) is False


def test_should_exclude_by_pattern():
    assert _should_exclude(Path("/tmp/file.pyc"), ["*.pyc"]) is True
    assert _should_exclude(Path("/tmp/file.py"), ["*.pyc"]) is False


def test_sync_directory_with_one_file():
    with tempfile.TemporaryDirectory() as src_dir:
        with tempfile.TemporaryDirectory() as repo_dir:
            src = Path(src_dir) / "hello.txt"
            src.write_text("hello")

            repo = RepoConfig(
                name="test",
                path=repo_dir,
                remotes=[],
                files=[FileEntry(source=str(src_dir), dest=".")],
                exclude=[],
            )

            result = sync_files(repo, Path("."))
            assert len(result.copied) >= 1
            assert (Path(repo_dir) / "hello.txt").exists()


def test_sync_single_file():
    with tempfile.TemporaryDirectory() as src_dir:
        with tempfile.TemporaryDirectory() as repo_dir:
            src_file = Path(src_dir) / "notes.txt"
            src_file.write_text("single file content")

            repo = RepoConfig(
                name="test",
                path=repo_dir,
                remotes=[],
                files=[FileEntry(source=str(src_file), dest=".")],
                exclude=[],
            )

            result = sync_files(repo, Path("."))
            assert len(result.copied) == 1
            assert result.copied[0] == str(src_file)
            assert (Path(repo_dir) / "notes.txt").exists()
            assert (Path(repo_dir) / "notes.txt").read_text() == "single file content"


def test_sync_skips_excluded_file():
    with tempfile.TemporaryDirectory() as src_dir:
        with tempfile.TemporaryDirectory() as repo_dir:
            (Path(src_dir) / "good.txt").write_text("ok")
            (Path(src_dir) / ".DS_Store").write_text("junk")

            repo = RepoConfig(
                name="test",
                path=repo_dir,
                remotes=[],
                files=[FileEntry(source=str(src_dir), dest=".")],
                exclude=[".DS_Store"],
            )

            result = sync_files(repo, Path("."))
            skipped = [s for s in result.skipped if ".DS_Store" in s]
            assert len(skipped) == 1
            assert not (Path(repo_dir) / ".DS_Store").exists()


def test_sync_missing_source():
    repo = RepoConfig(
        name="test",
        path="/tmp/repo",
        remotes=[],
        files=[FileEntry(source="/nonexistent/path", dest=".")],
        exclude=[],
    )

    result = sync_files(repo, Path("."))
    assert len(result.copied) == 0
    assert any("未找到" in s for s in result.skipped)


def test_sync_nested_directory():
    with tempfile.TemporaryDirectory() as src_dir:
        with tempfile.TemporaryDirectory() as repo_dir:
            nested = Path(src_dir) / "sub" / "deep"
            nested.mkdir(parents=True)
            (Path(src_dir) / "top.txt").write_text("top")
            (nested / "deep.txt").write_text("deep")

            repo = RepoConfig(
                name="test",
                path=repo_dir,
                remotes=[],
                files=[FileEntry(source=str(src_dir), dest=".")],
                exclude=[],
            )

            result = sync_files(repo, Path("."))
            assert len(result.copied) == 2
            assert (Path(repo_dir) / "top.txt").exists()
            assert (Path(repo_dir) / "sub" / "deep" / "deep.txt").exists()
