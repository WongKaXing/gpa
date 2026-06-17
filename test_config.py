"""Tests for config parsing."""
import tempfile
from pathlib import Path
from gitpush.config import parse_config, Config, RepoConfig, FileEntry


def test_parse_minimal_config():
    toml = """
[[repos]]
name = "test"
path = "/tmp/test"
remotes = ["origin"]
"""
    with tempfile.NamedTemporaryFile(mode="wb", suffix=".toml", delete=False) as f:
        f.write(toml.encode())
        tmp = Path(f.name)

    try:
        cfg = parse_config(tmp)
        assert len(cfg.repos) == 1
        assert cfg.repos[0].name == "test"
        assert cfg.repos[0].path == "/tmp/test"
        assert cfg.repos[0].remotes == ["origin"]
        assert cfg.repos[0].files == []
        assert cfg.repos[0].commit_template == "update {date}"
        assert cfg.repos[0].exclude == [".DS_Store", "__pycache__", "*.pyc"]
    finally:
        tmp.unlink()


def test_parse_with_files():
    toml = """
[[repos]]
name = "dots"
path = "~/dots"
remotes = ["gitee", "github"]

[[repos.files]]
source = "~/.config/nvim"
dest = "./"

[[repos.files]]
source = "~/.zshrc"
dest = "."
"""
    with tempfile.NamedTemporaryFile(mode="wb", suffix=".toml", delete=False) as f:
        f.write(toml.encode())
        tmp = Path(f.name)

    try:
        cfg = parse_config(tmp)
        assert len(cfg.repos[0].files) == 2
        assert cfg.repos[0].files[0].source == "~/.config/nvim"
        assert cfg.repos[0].files[1].dest == "."
    finally:
        tmp.unlink()


def test_defaults_override():
    toml = """
[defaults]
commit_template = "custom {date}"
exclude = [".git", "*.swp"]

[[repos]]
name = "a"
path = "/tmp/a"
remotes = []

[[repos]]
name = "b"
path = "/tmp/b"
remotes = []
commit_template = "override {date}"
"""
    with tempfile.NamedTemporaryFile(mode="wb", suffix=".toml", delete=False) as f:
        f.write(toml.encode())
        tmp = Path(f.name)

    try:
        cfg = parse_config(tmp)
        assert cfg.repos[0].commit_template == "custom {date}"
        assert cfg.repos[0].exclude == [".git", "*.swp"]
        assert cfg.repos[1].commit_template == "override {date}"
    finally:
        tmp.unlink()


def test_default_commit_template():
    cfg = Config(repos=[])
    assert cfg.commit_template == "update {date}"


def test_default_exclude():
    cfg = Config(repos=[])
    assert ".DS_Store" in cfg.exclude
    assert "__pycache__" in cfg.exclude
