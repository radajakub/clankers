from __future__ import annotations

import inspect
import logging
import time
from functools import wraps
from pathlib import Path
from types import TracebackType
from typing import Any, Callable, Coroutine, TypeVar, cast

from clankers.backends.backend import Backend
from clankers.backends.ntfy import NtfyBackend
from clankers.config import load_config
from clankers.models import Event

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


class Clanker:
    def __init__(
        self,
        *,
        config_path: str | Path | None = None,
        dotenv_path: str | Path | None = None,
        backend: Backend | None = None,
    ) -> None:
        self._config_path = config_path
        self._dotenv_path = dotenv_path
        self._backend = backend

    @property
    def backend(self) -> Backend:
        if self._backend is None:
            self._backend = NtfyBackend.from_config(load_config(path=self._config_path, dotenv_path=self._dotenv_path))
        return self._backend

    def send(self, event: Event) -> None:
        logger.debug("reporting %s", event.to_string())
        try:
            self.backend.send(event)
        except Exception as error:
            logger.warning("could not send notification: %s", error)

    def engage(self, message: str | None = None) -> Engage:
        return Engage(message, clanker=self)

    def rogerroger(self, message: str, duration: float | None = None) -> None:
        self.send(Event.rogerroger(message, duration))

    def uhoh(self, message: str, duration: float | None = None) -> None:
        self.send(Event.uhoh(message, duration))


_default: Clanker | None = None


def default() -> Clanker:
    global _default
    if _default is None:
        _default = Clanker()
    return _default


def configure(
    *,
    config_path: str | Path | None = None,
    dotenv_path: str | Path | None = None,
    backend: Backend | None = None,
) -> Clanker:
    global _default
    _default = Clanker(config_path=config_path, dotenv_path=dotenv_path, backend=backend)
    return _default


class Engage:
    def __init__(self, message: str | None = None, *, clanker: Clanker | None = None) -> None:
        if message is not None and not message.strip():
            raise ValueError("message cannot be empty")

        self.message = message
        self.clanker = clanker if clanker is not None else default()
        self._started_at: float | None = None

    def __enter__(self) -> Engage:
        if self.message is None:
            raise ValueError("a message is required when Engage is used as a context manager")
        self._started_at = time.monotonic()
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
        self.clanker.send(Event.from_exception(cast(str, self.message), duration, exc))
        return False

    def __call__(self, func: F) -> F:
        message = self.message if self.message is not None else func.__qualname__

        if inspect.iscoroutinefunction(func):
            coroutine_func = cast(Callable[..., Coroutine[Any, Any, Any]], func)

            @wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                with Engage(message, clanker=self.clanker):
                    return await coroutine_func(*args, **kwargs)

            return cast(F, async_wrapper)

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            with Engage(message, clanker=self.clanker):
                return func(*args, **kwargs)

        return cast(F, wrapper)


def engage(message: str | None = None) -> Engage:
    return default().engage(message)


def rogerroger(message: str, duration: float | None = None) -> None:
    default().rogerroger(message, duration)


def uhoh(message: str, duration: float | None = None) -> None:
    default().uhoh(message, duration)
