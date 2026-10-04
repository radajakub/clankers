from __future__ import annotations

from dataclasses import dataclass, field
from socket import gethostname

from clankers.core.themes import Status, Theme, label, validated_theme


@dataclass(frozen=True, slots=True)
class Event:
    message: str
    status: Status
    duration: float | None = None
    hostname: str = field(default_factory=gethostname)
    theme: Theme = "neutral"

    def __post_init__(self) -> None:
        if not self.message.strip():
            raise ValueError("event message cannot be empty")
        validated_theme(self.theme)

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

    def is_success(self) -> bool:
        return self.status == "rogerroger"

    def is_info(self) -> bool:
        return self.status == "blastthem"

    def is_failure(self) -> bool:
        return self.status == "uhoh"

    def to_string(self) -> str:
        duration = "" if self.duration is None else f" [{format_duration(self.duration)}]"
        return f"({self.hostname}){duration} {label(self.theme, self.status)}: {self.message}"


def describe(exc: BaseException) -> str:
    detail = str(exc)
    return f"{type(exc).__name__}: {detail}" if detail else type(exc).__name__


def format_duration(seconds: float) -> str:
    total_seconds = max(0, round(seconds))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}h {minutes}m {secs}s"
    if minutes:
        return f"{minutes}m {secs}s"
    return f"{secs}s"
