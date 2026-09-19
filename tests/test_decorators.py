from __future__ import annotations

import asyncio

import pytest
from conftest import RecordingBackend

import clankers
from clankers.core.models import Event


def test_decorator_reports_every_call() -> None:
    backend = RecordingBackend()

    @clankers.engage("Work", clanker=clankers.Clanker(backend=backend))
    def work(value: int) -> int:
        return value * 2

    assert work(3) == 6
    assert work(4) == 8
    assert backend.reported == [
        ("blastthem", "Work"),
        ("rogerroger", "Work"),
        ("blastthem", "Work"),
        ("rogerroger", "Work"),
    ]


def test_decorator_without_message_uses_the_function_name() -> None:
    backend = RecordingBackend()

    @clankers.engage(clanker=clankers.Clanker(backend=backend))
    def train() -> None:
        return None

    train()

    assert backend.events[0].message == "test_decorator_without_message_uses_the_function_name.<locals>.train"


def test_decorator_reports_failures_and_reraises() -> None:
    backend = RecordingBackend()

    @clankers.engage("Work", clanker=clankers.Clanker(backend=backend))
    def work() -> None:
        raise RuntimeError("broken")

    with pytest.raises(RuntimeError, match="broken"):
        work()

    assert backend.reported[-1] == ("uhoh", "Work: RuntimeError: broken")


def test_decorator_uses_the_shared_clanker_by_default() -> None:
    backend = RecordingBackend()
    clankers.configure(backend=backend)

    @clankers.engage("Work")
    def work() -> None:
        return None

    work()

    assert backend.reported == [("blastthem", "Work"), ("rogerroger", "Work")]


def test_async_decorator_waits_for_coroutine() -> None:
    backend = RecordingBackend()

    @clankers.engage("Async work", clanker=clankers.Clanker(backend=backend))
    async def work() -> str:
        await asyncio.sleep(0)
        return "done"

    assert asyncio.run(work()) == "done"
    assert backend.reported[-1] == ("rogerroger", "Async work")


def test_notification_error_does_not_hide_a_successful_result() -> None:
    class BrokenBackend:
        def send(self, event: Event) -> None:
            raise OSError("offline")

    @clankers.engage("Work", clanker=clankers.Clanker(backend=BrokenBackend()))
    def work() -> str:
        return "done"

    assert work() == "done"
