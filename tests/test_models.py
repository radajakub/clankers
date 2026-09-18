from __future__ import annotations

from socket import gethostname

import pytest

from clankers.models import Event, format_duration


def test_success_event_renders_host_duration_and_message() -> None:
    event = Event.rogerroger("pytest", 134)

    assert event.to_string() == f"({gethostname()}) [2m 14s] Roger, roger: pytest"


def test_event_without_duration_renders_without_brackets() -> None:
    event = Event.uhoh("deploy", None)

    assert event.to_string() == f"({gethostname()}) Uh-oh: deploy"


def test_empty_message_is_rejected() -> None:
    with pytest.raises(ValueError, match="message cannot be empty"):
        Event.rogerroger("  ", None)


def test_from_exception_reports_success_without_an_exception() -> None:
    event = Event.from_exception("Training", 3.0, None)

    assert event.success is True
    assert event.message == "Training"


def test_from_exception_describes_the_failure() -> None:
    event = Event.from_exception("Training", 3.0, RuntimeError("broken"))

    assert event.success is False
    assert event.message == "Training: RuntimeError: broken"


def test_from_exit_code_reports_success_for_zero() -> None:
    event = Event.from_exit_code("pytest", 1.0, 0)

    assert event.success is True
    assert event.message == "pytest"


def test_from_exit_code_reports_the_failing_status() -> None:
    event = Event.from_exit_code("pytest", 1.0, 7)

    assert event.success is False
    assert event.message == "pytest (exit code 7)"


def test_from_exit_code_appends_a_start_up_error() -> None:
    event = Event.from_exit_code("missing", 1.0, 127, FileNotFoundError("no such file"))

    assert event.message == "missing (exit code 127): FileNotFoundError: no such file"


@pytest.mark.parametrize(
    ("seconds", "formatted"),
    [(0.4, "0s"), (59, "59s"), (95, "1m 35s"), (3725, "1h 2m 5s")],
)
def test_durations_are_human_readable(seconds: float, formatted: str) -> None:
    assert format_duration(seconds) == formatted
