from __future__ import annotations

import logging
import time
from types import TracebackType
from typing import Callable

from clankers.core.clanker import Clanker
from clankers.core.models import describe
from clankers.default import default

logger = logging.getLogger(__name__)

MessageBuilder = Callable[[], str]
FailureBuilder = Callable[[BaseException], str]


class Engage:
    def __init__(
        self,
        message: str,
        *,
        clanker: Clanker | None = None,
        announce: bool = True,
        start: MessageBuilder | None = None,
        success: MessageBuilder | None = None,
        failure: FailureBuilder | None = None,
    ) -> None:
        self.message = validated(message)
        self.clanker = clanker if clanker is not None else default()
        self.announce = announce
        self._start = start
        self._success = success
        self._failure = failure
        self._started_at: float | None = None

    def __enter__(self) -> Engage:
        self._started_at = time.monotonic()
        if self.announce:
            self.clanker.blastthem(self._build(self._start, self.message))
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool:
        if self._started_at is None:
            raise RuntimeError("engage context was exited before it was entered")
        duration = time.monotonic() - self._started_at
        self._started_at = None
        self._report(exc, duration)
        return False

    def rogerroger(self, message: str, duration: float | None = None) -> None:
        self.clanker.rogerroger(message, duration)

    def blastthem(self, message: str, duration: float | None = None) -> None:
        self.clanker.blastthem(message, duration)

    def uhoh(self, message: str, duration: float | None = None) -> None:
        self.clanker.uhoh(message, duration)

    def _report(self, exc: BaseException | None, duration: float) -> None:
        if exc is None:
            self.clanker.rogerroger(self._build(self._success, self.message), duration)
            return

        failure = self._failure
        builder = None if failure is None else (lambda: failure(exc))
        self.clanker.uhoh(self._build(builder, f"{self.message}: {describe(exc)}"), duration)

    def _build(self, builder: MessageBuilder | None, fallback: str) -> str:
        if builder is None:
            return fallback
        # A message the caller builds must never break, or replace, the work being reported.
        try:
            return validated(builder())
        except Exception as error:
            logger.warning("could not build a notification message: %s", error)
            return fallback


def validated(message: str) -> str:
    if not message.strip():
        raise ValueError("message cannot be empty")
    return message
