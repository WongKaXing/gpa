"""测试 gpa 设置文件（settings.toml）的加载与排序工具。"""
from gitpush.settings import (
    Settings,
    SETTINGS_TEMPLATE,
    ensure_settings,
    load_settings,
    order_repos,
)
from gitpush.config import RepoConfig


def _repo(name: str) -> RepoConfig:
    return RepoConfig(name=name, path=f"/tmp/{name}", remotes=[])


def test_default_settings_no_file(_isolate_settings) -> None:
    """无设置文件时返回默认值。"""
    settings = load_settings()
    assert settings.sort_order == "asc"
    assert settings.show_usage is True
    assert settings.color is True
    assert settings.default_action == "menu"


def test_load_custom_settings(_isolate_settings, tmp_path) -> None:
    """正常解析设置文件。"""
    path = tmp_path / "custom.toml"
    path.write_text('sort_order = "desc"\nshow_usage = false\ncolor = false\ndefault_action = "push"\n')

    settings = load_settings(path)

    assert settings.sort_order == "desc"
    assert settings.show_usage is False
    assert settings.color is False
    assert settings.default_action == "push"


def test_invalid_fields_fall_back(_isolate_settings, tmp_path) -> None:
    """非法字段回退默认值，宽松解析不报错。"""
    path = tmp_path / "bad.toml"
    path.write_text('sort_order = "sideways"\nshow_usage = "yes"\ndefault_action = "fly"\ncolor = 1\n')

    settings = load_settings(path)

    assert settings.sort_order == "asc"
    assert settings.show_usage is True
    assert settings.default_action == "menu"
    assert settings.color is True


def test_corrupted_file_falls_back(_isolate_settings, tmp_path) -> None:
    """损坏的设置文件回退默认值。"""
    path = tmp_path / "broken.toml"
    path.write_text("not [valid toml")

    settings = load_settings(path)

    assert settings == Settings()


def test_ensure_settings_creates_template(_isolate_settings) -> None:
    """首次运行自动生成带注释的设置模板。"""
    path = ensure_settings()

    assert path.exists()
    text = path.read_text()
    # 模板中列出全部可配置参数
    assert "sort_order" in text
    assert "show_usage" in text
    assert "color" in text
    assert "default_action" in text
    assert "gpa 设置文件" in text


def test_ensure_settings_idempotent(_isolate_settings) -> None:
    """已存在时不覆盖。"""
    first = ensure_settings()
    first.write_text("# 用户自定义内容\n")
    ensure_settings()
    assert first.read_text() == "# 用户自定义内容\n"


def test_order_repos_asc(_isolate_settings) -> None:
    repos = [_repo("zsh"), _repo("alpha"), _repo("Beta")]
    ordered = order_repos(repos, "asc")
    assert [r.name for r in ordered] == ["alpha", "Beta", "zsh"]


def test_order_repos_desc(_isolate_settings) -> None:
    repos = [_repo("zsh"), _repo("alpha"), _repo("Beta")]
    ordered = order_repos(repos, "desc")
    assert [r.name for r in ordered] == ["zsh", "Beta", "alpha"]


def test_order_repos_config(_isolate_settings) -> None:
    repos = [_repo("zsh"), _repo("alpha"), _repo("Beta")]
    ordered = order_repos(repos, "config")
    assert [r.name for r in ordered] == ["zsh", "alpha", "Beta"]


def test_settings_template_parses(_isolate_settings, tmp_path) -> None:
    """生成的模板本身能被正常解析为默认值。"""
    path = tmp_path / "settings.toml"
    path.write_text(SETTINGS_TEMPLATE)
    settings = load_settings(path)
    assert settings == Settings()
