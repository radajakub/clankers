from __future__ import annotations

import logging
import os
import tomllib
from pathlib import Path

from dotenv import dotenv_values, find_dotenv

logger = logging.getLogger(__name__)

Config = dict[str, object]

# Process environment variables are only picked up under this prefix so that the
# configuration mapping stays a description of clankers, not a copy of os.environ.
ENV_PREFIX = "NTFY_"


class ConfigError(ValueError):
    pass


def default_config_path(env: dict[str, str] | None = None) -> Path:
    environ = os.environ if env is None else env
    if xdg_home := environ.get("XDG_CONFIG_HOME"):
        return Path(xdg_home).expanduser() / "clankers" / "config.toml"
    return Path.home() / ".config" / "clankers" / "config.toml"


def load_config(
    *,
    path: str | Path | None = None,
    dotenv_path: str | Path | None = None,
    env: dict[str, str] | None = None,
) -> Config:
    environ = os.environ if env is None else env

    dotenv_file = _find_dotenv_path(dotenv_path)
    dotenv_config = _defined_values(dotenv_values(dotenv_file)) if dotenv_file is not None else {}

    values: Config = _read_toml(_config_path(path, environ))
    values.update(_environment_values(environ))
    values.update(dotenv_config)
    logger.debug("configuration provides %s", ", ".join(sorted(values)) or "nothing")
    return values


def _config_path(path: str | Path | None, env: dict[str, str]) -> Path:
    if path is not None:
        return Path(path).expanduser()
    return default_config_path(env)


def _read_toml(path: Path) -> Config:
    if not path.is_file():
        logger.debug("no config file at %s", path)
        return {}
    logger.debug("reading config file %s", path)
    try:
        with path.open("rb") as config_file:
            return _flatten(tomllib.load(config_file))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise ConfigError(f"could not read config {path}: {exc}") from exc


def _flatten(values: dict[str, object], prefix: str = "") -> Config:
    flattened: Config = {}
    for key, value in values.items():
        normalized_key = key.upper()
        full_key = f"{prefix}_{normalized_key}" if prefix else normalized_key
        if isinstance(value, dict):
            flattened.update(_flatten(value, full_key))
        else:
            flattened[full_key] = value
    return flattened


def _environment_values(env: dict[str, str]) -> Config:
    return {key: value for key, value in env.items() if key.startswith(ENV_PREFIX) and value != ""}


def _defined_values(values: dict[str, object | None]) -> Config:
    return {key: value for key, value in values.items() if value is not None and value != ""}


def _find_dotenv_path(path: str | Path | None) -> Path | None:
    if path is not None:
        return Path(path).expanduser()
    discovered = find_dotenv(usecwd=True)
    if not discovered:
        logger.debug("no .env found above %s", Path.cwd())
        return None
    logger.debug("reading .env file %s", discovered)
    return Path(discovered)
