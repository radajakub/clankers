from __future__ import annotations

import logging
from pathlib import Path

from clankers.backends.backend import Backend
from clankers.backends.ntfy import NtfyBackend
from clankers.config import load_config
from clankers.core.models import Event, Status

logger = logging.getLogger(__name__)


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

    def notify(self, status: Status, message: str, duration: float | None = None) -> None:
        self.send(Event.of(status, message, duration))

    def rogerroger(self, message: str, duration: float | None = None) -> None:
        self.notify("rogerroger", message, duration)

    def blastthem(self, message: str, duration: float | None = None) -> None:
        self.notify("blastthem", message, duration)

    def uhoh(self, message: str, duration: float | None = None) -> None:
        self.notify("uhoh", message, duration)
