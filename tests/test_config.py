from __future__ import annotations

from pathlib import Path

import pytest

from clankers.config import ConfigError, default_config_path, load_config


@pytest.fixture(autouse=True)
def isolate_repository_dotenv(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.chdir(tmp_path)


def test_flattens_backend_tables_into_normalized_keys(tmp_path: Path) -> None:
    path = tmp_path / "config.toml"
    path.write_text('[ntfy]\nurl = "https://ntfy.example.com"\ntopic = "default"\ntoken = "file-token"\ntimeout = 4\n')

    config = load_config(path=path, env={})

    assert config == {
        "NTFY_URL": "https://ntfy.example.com",
        "NTFY_TOPIC": "default",
        "NTFY_TOKEN": "file-token",
        "NTFY_TIMEOUT": 4,
    }


def test_loader_does_not_add_backend_defaults(tmp_path: Path) -> None:
    config = load_config(path=tmp_path / "missing.toml", env={})

    assert config == {}


def test_dotenv_has_priority_over_environment_and_toml(tmp_path: Path) -> None:
    toml_path = tmp_path / "config.toml"
    toml_path.write_text('[ntfy]\nurl = "https://toml.example"\ntopic = "toml"\n')
    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text("NTFY_URL=https://dotenv.example\nNTFY_TOPIC=dotenv\n")

    config = load_config(
        path=toml_path,
        dotenv_path=dotenv_path,
        env={"NTFY_URL": "https://environment.example", "NTFY_TOPIC": "environment"},
    )

    assert config["NTFY_URL"] == "https://dotenv.example"
    assert config["NTFY_TOPIC"] == "dotenv"


def test_preserves_keys_for_other_backends(tmp_path: Path) -> None:
    path = tmp_path / "config.toml"
    path.write_text('[slack]\nwebhook_url = "https://hooks.example"\n')

    config = load_config(path=path, env={})

    assert config == {"SLACK_WEBHOOK_URL": "https://hooks.example"}


def test_discovers_dotenv_from_working_directory(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    (tmp_path / ".env").write_text("NTFY_TOPIC=discovered\n")
    child = tmp_path / "project" / "scripts"
    child.mkdir(parents=True)
    monkeypatch.chdir(child)

    config = load_config(path=tmp_path / "missing.toml", env={})

    assert config["NTFY_TOPIC"] == "discovered"


def test_default_path_uses_xdg_config_home() -> None:
    assert default_config_path({"XDG_CONFIG_HOME": "/settings"}) == Path("/settings/clankers/config.toml")


def test_reports_invalid_toml(tmp_path: Path) -> None:
    path = tmp_path / "config.toml"
    path.write_text("[ntfy\n")

    with pytest.raises(ConfigError, match="could not read config"):
        load_config(path=path, env={})


def test_environment_wins_over_toml(tmp_path: Path) -> None:
    toml_path = tmp_path / "config.toml"
    toml_path.write_text('[ntfy]\nurl = "https://toml.example"\ntopic = "toml"\n')

    config = load_config(path=toml_path, env={"NTFY_TOPIC": "environment"})

    assert config["NTFY_URL"] == "https://toml.example"
    assert config["NTFY_TOPIC"] == "environment"


def test_only_clankers_environment_variables_are_collected(tmp_path: Path) -> None:
    config = load_config(path=tmp_path / "missing.toml", env={"PATH": "/usr/bin", "NTFY_TOPIC": "jobs"})

    assert config == {"NTFY_TOPIC": "jobs"}
