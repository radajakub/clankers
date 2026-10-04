from __future__ import annotations

from dataclasses import replace
from socket import gethostname

import pytest

from clankers.core.models import Event, format_duration


def test_success_event_renders_host_duration_and_message() -> None:
    event = Event.rogerroger("pytest", 134)

    assert event.to_string() == f"({gethostname()}) [2m 14s] Done: pytest"


def test_neutral_event_renders_its_own_label() -> None:
    event = Event.blastthem("pytest started")

    assert event.to_string() == f"({gethostname()}) Info: pytest started"


def test_event_without_duration_renders_without_brackets() -> None:
    event = Event.uhoh("deploy", None)

    assert event.to_string() == f"({gethostname()}) Failed: deploy"


def test_empty_message_is_rejected() -> None:
    with pytest.raises(ValueError, match="message cannot be empty"):
        Event.rogerroger("  ", None)


def test_of_builds_any_status() -> None:
    assert Event.of("blastthem", "halfway", 3.0).status == "blastthem"


def test_from_exit_code_reports_success_for_zero() -> None:
    event = Event.from_exit_code("pytest", 1.0, 0)

    assert event.status == "rogerroger"
    assert event.message == "pytest"


def test_from_exit_code_reports_the_failing_status() -> None:
    event = Event.from_exit_code("pytest", 1.0, 7)

    assert event.status == "uhoh"
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


def test_starwars_theme_renders_its_own_labels() -> None:
    event = Event("pytest", "rogerroger", 134, hostname="host", theme="starwars")

    assert event.to_string() == "(host) [2m 14s] Roger, roger: pytest"
    assert replace(event, status="blastthem").to_string() == "(host) [2m 14s] Blast them!: pytest"
    assert replace(event, status="uhoh").to_string() == "(host) [2m 14s] Uh-oh: pytest"


def test_unknown_theme_is_rejected() -> None:
    with pytest.raises(ValueError, match="unknown theme"):
        Event("pytest", "rogerroger", theme="startrek")  # type: ignore[arg-type]


@pytest.mark.parametrize("status", ["rogerroger", "blastthem", "uhoh"])
def test_status_helpers_match_only_their_own_status(status: str) -> None:
    event = Event.of(status, "pytest")  # type: ignore[arg-type]

    assert [event.is_success(), event.is_info(), event.is_failure()] == [status == "rogerroger", status == "blastthem", status == "uhoh"]
