from __future__ import annotations

import logging

import pytest
from conftest import RecordingBackend

import clankers
from clankers.core.context import MessageBuilder
from clankers.core.models import Event


def test_context_manager_announces_the_start_and_the_success(backend: RecordingBackend) -> None:
    with clankers.Engage("Training"):
        pass

    assert backend.reported == [("blastthem", "Training"), ("rogerroger", "Training")]
    start, end = backend.events
    assert start.duration is None
    assert end.duration >= 0
    assert not hasattr(end, "topic")


def test_context_manager_can_stay_quiet_until_it_finishes(backend: RecordingBackend) -> None:
    with clankers.Engage("Training", announce=False):
        pass

    assert backend.reported == [("rogerroger", "Training")]


def test_context_manager_rejects_an_empty_message() -> None:
    with pytest.raises(ValueError, match="message cannot be empty"):
        clankers.Engage("   ")


def test_context_manager_reports_and_reraises_exception(backend: RecordingBackend) -> None:
    with pytest.raises(RuntimeError, match="broken"):
        with clankers.Engage("Training", announce=False):
            raise RuntimeError("broken")

    assert backend.reported == [("uhoh", "Training: RuntimeError: broken")]


def test_builders_describe_every_phase(backend: RecordingBackend) -> None:
    state = {"epoch": 0}

    with clankers.Engage(
        "Training",
        start=lambda: f"Training from epoch {state['epoch']}",
        success=lambda: f"Training reached epoch {state['epoch']}",
    ):
        state["epoch"] = 7

    assert backend.reported == [
        ("blastthem", "Training from epoch 0"),
        ("rogerroger", "Training reached epoch 7"),
    ]


def test_failure_builder_receives_the_exception(backend: RecordingBackend) -> None:
    with pytest.raises(RuntimeError):
        with clankers.Engage("Training", announce=False, failure=lambda exc: f"Training died: {exc}"):
            raise RuntimeError("broken")

    assert backend.reported == [("uhoh", "Training died: broken")]


def _blank_message() -> str:
    return "   "


def _broken_builder() -> str:
    raise RuntimeError("no state to report")


@pytest.mark.parametrize("builder", [_blank_message, _broken_builder])
def test_an_unusable_builder_falls_back_to_the_message(
    builder: MessageBuilder,
    backend: RecordingBackend,
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.WARNING, logger="clankers.core.context"):
        with clankers.Engage("Training", announce=False, success=builder):
            pass

    assert backend.reported == [("rogerroger", "Training")]
    assert "could not build a notification message" in caplog.text


def test_context_handles_send_extra_notifications_without_replacing_the_report(backend: RecordingBackend) -> None:
    with clankers.Engage("Benchmark", announce=False) as engage:
        engage.rogerroger("Matchup 1 complete")
        engage.blastthem("Matchup 2 started")
        engage.uhoh("Matchup 2 crashed", 12.0)

    assert backend.reported == [
        ("rogerroger", "Matchup 1 complete"),
        ("blastthem", "Matchup 2 started"),
        ("uhoh", "Matchup 2 crashed"),
        ("rogerroger", "Benchmark"),
    ]
    assert backend.events[2].duration == 12.0


def test_a_named_clanker_reports_instead_of_the_shared_one(backend: RecordingBackend) -> None:
    private = RecordingBackend()

    with clankers.Engage("Benchmark", clanker=clankers.Clanker(backend=private), announce=False) as engage:
        engage.rogerroger("Halfway")

    assert [event.message for event in private.events] == ["Halfway", "Benchmark"]
    assert backend.events == []


def test_notification_error_does_not_hide_task_error(caplog: pytest.LogCaptureFixture) -> None:
    class BrokenBackend:
        def send(self, event: Event) -> None:
            raise OSError("offline")

    with caplog.at_level(logging.WARNING, logger="clankers.core.context"):
        with pytest.raises(LookupError, match="task failed"):
            with clankers.Engage("Work", clanker=clankers.Clanker(backend=BrokenBackend())):
                raise LookupError("task failed")

    assert "offline" in caplog.text


def test_exiting_before_entering_is_an_error(backend: RecordingBackend) -> None:
    context = clankers.Engage("Work")

    with pytest.raises(RuntimeError, match="before it was entered"):
        context.__exit__(None, None, None)
