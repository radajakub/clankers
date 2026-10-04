from __future__ import annotations

from pathlib import Path

import pytest

import clankers
from clankers.core.models import Event


class RecordingBackend:
    def __init__(self) -> None:
        self.events: list[Event] = []

    def send(self, event: Event) -> None:
        self.events.append(event)

    @property
    def reported(self) -> list[tuple[str, str]]:
        return [(event.status, event.message) for event in self.events]


@pytest.fixture(autouse=True)
def isolate_configuration(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # Keep the developer's own config, .env and theme out of every test.
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.delenv("CLANKERS_THEME", raising=False)
    monkeypatch.chdir(tmp_path)


@pytest.fixture(autouse=True)
def unresolved_default_clanker() -> None:
    clankers.configure()


@pytest.fixture
def backend() -> RecordingBackend:
    recording = RecordingBackend()
    clankers.configure(backend=recording)
    return recording
