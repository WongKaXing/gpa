"""End-to-end integration tests with real git repos."""
import subprocess
import tempfile
from pathlib import Path
from gitpush.config import parse_config
from gitpush.orchestrator import run_all


def _init_repo(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init"], cwd=path, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=path, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=path, capture_output=True)
    (path / ".keep").write_text("")
    subprocess.run(["git", "add", "-A"], cwd=path, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=path, capture_output=True)


def _init_bare(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "--bare", str(path)], capture_output=True)


def test_full_flow_with_push():
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)

        # Setup source files
        src = tmp / "configs"
        src.mkdir()
        (src / "starship.toml").write_text("format = '$all'")
        (src / ".DS_Store").write_text("junk")
        sub_src = src / "nvim"
        sub_src.mkdir()
        (sub_src / "init.lua").write_text("vim.opt.number = true")

        # Setup git repo
        repo = tmp / "dots"
        _init_repo(repo)

        # Setup bare remote
        bare = tmp / "bare.git"
        _init_bare(bare)
        subprocess.run(
            ["git", "remote", "add", "origin", str(bare)],
            cwd=repo, capture_output=True,
        )

        # Write config
        config_toml = f"""
[defaults]
commit_template = "update {{date}}"
exclude = [".DS_Store"]

[[repos]]
name = "dots"
path = "{repo}"
remotes = ["origin"]

[[repos.files]]
source = "{src}"
dest = "."
"""
        config_path = tmp / "gitpush.toml"
        config_path.write_text(config_toml)

        # Run
        config = parse_config(config_path)
        run_all(config, config_path, verbose=True)

        # Verify files were copied (excluding .DS_Store)
        assert (repo / "starship.toml").exists()
        assert (repo / "nvim" / "init.lua").exists()
        assert not (repo / ".DS_Store").exists()

        # Verify commit was made
        log = subprocess.run(
            ["git", "log", "--oneline"],
            cwd=repo, capture_output=True, text=True,
        )
        assert "update" in log.stdout
