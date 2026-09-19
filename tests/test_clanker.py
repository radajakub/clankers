from __future__ import annotations

import logging
from pathlib import Path

import pytest
from conftest import RecordingBackend

import clankers
from clankers.core.models import Event


def test_package_exports_entry_points() -> None:
    assert callable(clankers.engage)
    assert clankers.Engage is not None


def test_manual_notifications_report_every_status() -> None:
    recording = RecordingBackend()
    clanker = clankers.Clanker(backend=recording)

    clanker.rogerroger("deploy finished")
    clanker.blastthem("deploy started")
    clanker.uhoh("deploy failed", 12.0)

    assert recording.reported == [
        ("rogerroger", "deploy finished"),
        ("blastthem", "deploy started"),
        ("uhoh", "deploy failed"),
    ]
    assert recording.events[2].duration == 12.0


def test_module_level_notifications_use_the_shared_clanker(backend: RecordingBackend) -> None:
    clankers.rogerroger("done")
    clankers.blastthem("halfway")
    clankers.uhoh("failed")

    assert [status for status, _ in backend.reported] == ["rogerroger", "blastthem", "uhoh"]


def test_backend_is_built_from_the_loaded_config(monkeypatch: pytest.MonkeyPatch) -> None:
    recording = RecordingBackend()
    config = {"NTFY_URL": "https://ntfy.example", "NTFY_TOPIC": "jobs"}
    monkeypatch.setattr("clankers.core.clanker.load_config", lambda **kwargs: config)
    monkeypatch.setattr("clankers.core.clanker.NtfyBackend.from_config", lambda values: recording)

    clankers.Clanker().rogerroger("Configured work")

    assert recording.events[0].message == "Configured work"


def test_configuration_is_loaded_once_and_lazily(monkeypatch: pytest.MonkeyPatch) -> None:
    loaded: list[dict[str, object]] = []
    recording = RecordingBackend()
    monkeypatch.setattr("clankers.core.clanker.load_config", lambda **kwargs: loaded.append(kwargs) or {})
    monkeypatch.setattr("clankers.core.clanker.NtfyBackend.from_config", lambda values: recording)

    clanker = clankers.Clanker(config_path=Path("config.toml"))
    assert loaded == []

    clanker.rogerroger("first")
    clanker.rogerroger("second")

    assert [kwargs["path"] for kwargs in loaded] == [Path("config.toml")]
    assert len(recording.events) == 2


def test_delivery_failures_are_logged_and_swallowed(caplog: pytest.LogCaptureFixture) -> None:
    class BrokenBackend:
        def send(self, event: Event) -> None:
            raise OSError("offline")

    with caplog.at_level(logging.WARNING, logger="clankers.core.clanker"):
        clankers.Clanker(backend=BrokenBackend()).rogerroger("done")

    assert "offline" in caplog.text
