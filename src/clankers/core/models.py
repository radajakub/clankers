from __future__ import annotations

from dataclasses import dataclass, field
from socket import gethostname
from typing import Literal

Status = Literal["rogerroger", "blastthem", "uhoh"]

_LABELS: dict[Status, str] = {
    "rogerroger": "Roger, roger",
    "blastthem": "Blast them!",
    "uhoh": "Uh-oh",
}


@dataclass(frozen=True, slots=True)
class Event:
    message: str
    status: Status
    duration: float | None = None
    hostname: str = field(default_factory=gethostname)

    def __post_init__(self) -> None:
        if not self.message.strip():
            raise ValueError("event message cannot be empty")

    @staticmethod
    def of(status: Status, message: str, duration: float | None = None) -> Event:
        return Event(message, status, duration)

    @staticmethod
    def rogerroger(message: str, duration: float | None = None) -> Event:
        return Event(message, "rogerroger", duration)

    @staticmethod
    def blastthem(message: str, duration: float | None = None) -> Event:
        return Event(message, "blastthem", duration)

    @staticmethod
    def uhoh(message: str, duration: float | None = None) -> Event:
        return Event(message, "uhoh", duration)

    @classmethod
    def from_exit_code(cls, command: str, duration: float | None, exit_code: int, exc: OSError | None = None) -> Event:
        # success
        if exit_code == 0:
            return cls.rogerroger(command, duration)

        message = f"{command} (exit code {exit_code})"

        return cls.uhoh(message if exc is None else f"{message}: {describe(exc)}", duration)

    def to_string(self) -> str:
        duration = "" if self.duration is None else f" [{format_duration(self.duration)}]"
        return f"({self.hostname}){duration} {_LABELS[self.status]}: {self.message}"


def describe(exc: BaseException) -> str:
    return f"{type(exc).__name__}: {exc}"


def format_duration(seconds: float) -> str:
    total_seconds = max(0, round(seconds))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}h {minutes}m {secs}s"
    if minutes:
        return f"{minutes}m {secs}s"
    return f"{secs}s"
