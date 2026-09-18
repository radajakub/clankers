from __future__ import annotations

from dataclasses import dataclass, field
from socket import gethostname


@dataclass(frozen=True, slots=True)
class Event:
    message: str
    success: bool
    duration: float | None
    hostname: str = field(default_factory=gethostname)

    def __post_init__(self) -> None:
        if not self.message.strip():
            raise ValueError("event message cannot be empty")

    @staticmethod
    def uhoh(message: str, duration: float | None) -> Event:
        return Event(message, False, duration)

    @staticmethod
    def rogerroger(message: str, duration: float | None) -> Event:
        return Event(message, True, duration)

    @classmethod
    def from_exception(cls, message: str, duration: float | None, exc: BaseException | None) -> Event:
        if exc is None:
            return cls.rogerroger(message, duration)
        return cls.uhoh(f"{message}: {_describe(exc)}", duration)

    @classmethod
    def from_exit_code(cls, command: str, duration: float | None, exit_code: int, exc: OSError | None = None) -> Event:
        # success
        if exit_code == 0:
            return cls.rogerroger(command, duration)

        message = f"{command} (exit code {exit_code})"

        return cls.uhoh(message if exc is None else f"{message}: {_describe(exc)}", duration)

    def to_string(self) -> str:
        status = "Roger, roger" if self.success else "Uh-oh"
        duration = "" if self.duration is None else f" [{format_duration(self.duration)}]"
        return f"({self.hostname}){duration} {status}: {self.message}"


def _describe(exc: BaseException) -> str:
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
