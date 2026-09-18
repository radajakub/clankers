from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import pytest

import clankers
from clankers.models import Event


class RecordingBackend:
    def __init__(self) -> None:
        self.events: list[Event] = []

    def send(self, event: Event) -> None:
        self.events.append(event)


@pytest.fixture(autouse=True)
def unresolved_default_clanker() -> None:
    clankers.configure()


def test_package_exports_entry_points() -> None:
    assert callable(clankers.engage)
    assert clankers.Engage is not None


def test_context_manager_reports_success_without_backend_configuration() -> None:
    backend = RecordingBackend()

    with clankers.Clanker(backend=backend).engage("Training"):
        pass

    [event] = backend.events
    assert event.message == "Training"
    assert event.success is True
    assert not hasattr(event, "topic")
    assert event.duration >= 0
    assert event.hostname


def test_context_manager_requires_a_message() -> None:
    with pytest.raises(ValueError, match="message is required"):
        with clankers.Clanker(backend=RecordingBackend()).engage():
            pass


def test_context_manager_builds_backend_from_loaded_config(monkeypatch: pytest.MonkeyPatch) -> None:
    backend = RecordingBackend()
    config = {"NTFY_URL": "https://ntfy.example", "NTFY_TOPIC": "jobs"}
    monkeypatch.setattr("clankers.core.load_config", lambda **kwargs: config)
    monkeypatch.setattr("clankers.core.NtfyBackend.from_config", lambda values: backend)

    with clankers.engage("Configured work"):
        pass

    assert backend.events[0].message == "Configured work"


def test_configuration_is_loaded_lazily(monkeypatch: pytest.MonkeyPatch) -> None:
    loaded: list[dict[str, object]] = []
    backend = RecordingBackend()
    monkeypatch.setattr("clankers.core.load_config", lambda **kwargs: loaded.append(kwargs) or {})
    monkeypatch.setattr("clankers.core.NtfyBackend.from_config", lambda values: backend)

    task = clankers.Clanker(config_path=Path("config.toml")).engage()(lambda: None)
    assert loaded == []

    task()
    task()

    assert [kwargs["path"] for kwargs in loaded] == [Path("config.toml")]
    assert len(backend.events) == 2


def test_context_manager_reports_and_reraises_exception() -> None:
    backend = RecordingBackend()

    with pytest.raises(RuntimeError, match="broken"):
        with clankers.Clanker(backend=backend).engage("Training"):
            raise RuntimeError("broken")

    [event] = backend.events
    assert event.success is False
    assert event.message == "Training: RuntimeError: broken"


def test_decorator_reports_every_call() -> None:
    backend = RecordingBackend()

    @clankers.Clanker(backend=backend).engage("Work")
    def work(value: int) -> int:
        return value * 2

    assert work(3) == 6
    assert work(4) == 8
    assert [event.success for event in backend.events] == [True, True]


def test_decorator_without_message_uses_the_function_name() -> None:
    backend = RecordingBackend()

    @clankers.Clanker(backend=backend).engage()
    def train() -> None:
        return None

    train()

    assert backend.events[0].message == "test_decorator_without_message_uses_the_function_name.<locals>.train"


def test_decorator_reports_failures_and_reraises() -> None:
    backend = RecordingBackend()

    @clankers.Clanker(backend=backend).engage("Work")
    def work() -> None:
        raise RuntimeError("broken")

    with pytest.raises(RuntimeError, match="broken"):
        work()

    assert backend.events[0].message == "Work: RuntimeError: broken"


def test_async_decorator_waits_for_coroutine() -> None:
    backend = RecordingBackend()

    @clankers.Clanker(backend=backend).engage("Async work")
    async def work() -> str:
        await asyncio.sleep(0)
        return "done"

    assert asyncio.run(work()) == "done"
    assert backend.events[0].success is True


def test_notification_error_does_not_hide_task_error(caplog: pytest.LogCaptureFixture) -> None:
    class BrokenBackend:
        def send(self, event: Event) -> None:
            raise OSError("offline")

    with caplog.at_level(logging.WARNING, logger="clankers.core"):
        with pytest.raises(LookupError, match="task failed"):
            with clankers.Clanker(backend=BrokenBackend()).engage("Work"):
                raise LookupError("task failed")

    assert "offline" in caplog.text


def test_notification_error_does_not_hide_a_successful_result(caplog: pytest.LogCaptureFixture) -> None:
    class BrokenBackend:
        def send(self, event: Event) -> None:
            raise OSError("offline")

    @clankers.Clanker(backend=BrokenBackend()).engage("Work")
    def work() -> str:
        return "done"

    with caplog.at_level(logging.WARNING, logger="clankers.core"):
        assert work() == "done"

    assert "offline" in caplog.text


def test_missing_configuration_only_warns(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    monkeypatch.setattr("clankers.core.load_config", lambda **kwargs: {})

    @clankers.engage("Work")
    def work() -> str:
        return "done"

    with caplog.at_level(logging.WARNING, logger="clankers.core"):
        assert work() == "done"

    assert "NTFY_URL" in caplog.text


def test_manual_notifications_report_both_outcomes() -> None:
    backend = RecordingBackend()

    clanker = clankers.Clanker(backend=backend)

    clanker.rogerroger("Model uploaded")
    clanker.uhoh("Model rejected", 12.0)

    success, failure = backend.events
    assert (success.message, success.success, success.duration) == ("Model uploaded", True, None)
    assert (failure.message, failure.success, failure.duration) == ("Model rejected", False, 12.0)


def test_manual_notifications_use_the_configured_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    backend = RecordingBackend()
    monkeypatch.setattr("clankers.core.load_config", lambda **kwargs: {"NTFY_URL": "https://ntfy.example", "NTFY_TOPIC": "jobs"})
    monkeypatch.setattr("clankers.core.NtfyBackend.from_config", lambda values: backend)

    clankers.rogerroger("Done")

    assert backend.events[0].message == "Done"


def test_manual_notification_only_warns_when_it_cannot_be_sent(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    monkeypatch.setattr("clankers.core.load_config", lambda **kwargs: {})

    with caplog.at_level(logging.WARNING, logger="clankers.core"):
        clankers.uhoh("Something broke")

    assert "NTFY_URL" in caplog.text


def test_default_clanker_loads_the_configuration_once(monkeypatch: pytest.MonkeyPatch) -> None:
    loads: list[dict[str, object]] = []
    backend = RecordingBackend()
    monkeypatch.setattr("clankers.core.load_config", lambda **kwargs: loads.append(kwargs) or {})
    monkeypatch.setattr("clankers.core.NtfyBackend.from_config", lambda values: backend)

    @clankers.engage("Decorated")
    def work() -> None:
        return None

    work()
    with clankers.Engage("Block"):
        pass
    clankers.rogerroger("Manual")

    assert len(loads) == 1
    assert [event.message for event in backend.events] == ["Decorated", "Block", "Manual"]


def test_configure_replaces_the_default_clanker() -> None:
    backend = RecordingBackend()

    clanker = clankers.configure(backend=backend)

    assert clankers.default() is clanker
    clankers.uhoh("Manual")
    with clankers.Engage("Block"):
        pass
    assert [event.message for event in backend.events] == ["Manual", "Block"]


def test_a_private_clanker_leaves_the_default_untouched() -> None:
    shared = RecordingBackend()
    private = RecordingBackend()
    clankers.configure(backend=shared)

    clankers.Clanker(backend=private).rogerroger("Private")

    assert [event.message for event in private.events] == ["Private"]
    assert shared.events == []


def test_clanker_exposes_every_way_of_reporting() -> None:
    clanker = clankers.Clanker(backend=(backend := RecordingBackend()))

    clanker.rogerroger("Manual")
    with clanker.engage("Block"):
        pass

    @clanker.engage()
    def work() -> None:
        return None

    work()

    assert [event.message for event in backend.events] == ["Manual", "Block", "test_clanker_exposes_every_way_of_reporting.<locals>.work"]
