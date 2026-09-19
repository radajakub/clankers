from __future__ import annotations

from pathlib import Path

from clankers.backends.backend import Backend
from clankers.core.clanker import Clanker

_default: Clanker | None = None


def default() -> Clanker:
    global _default
    if _default is None:
        _default = Clanker()
    return _default


def configure(
    *,
    config_path: str | Path | None = None,
    dotenv_path: str | Path | None = None,
    backend: Backend | None = None,
) -> Clanker:
    global _default
    _default = Clanker(config_path=config_path, dotenv_path=dotenv_path, backend=backend)
    return _default


def rogerroger(message: str, duration: float | None = None) -> None:
    default().rogerroger(message, duration)


def blastthem(message: str, duration: float | None = None) -> None:
    default().blastthem(message, duration)


def uhoh(message: str, duration: float | None = None) -> None:
    default().uhoh(message, duration)
