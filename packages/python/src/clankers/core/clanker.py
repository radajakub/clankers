from __future__ import annotations

import logging
from dataclasses import replace
from pathlib import Path

from clankers.backends.backend import Backend
from clankers.backends.ntfy import NtfyBackend
from clankers.config import Config, load_config, optional_string
from clankers.core.models import Event, Status
from clankers.core.themes import Theme, validated_theme

logger = logging.getLogger(__name__)


class Clanker:
    def __init__(
        self,
        *,
        config_path: str | Path | None = None,
        dotenv_path: str | Path | None = None,
        backend: Backend | None = None,
        theme: Theme | None = None,
    ) -> None:
        self._config_path = config_path
        self._dotenv_path = dotenv_path
        self._backend = backend
        self._theme: Theme | None = None if theme is None else validated_theme(theme)
        self._config: Config | None = None

    @property
    def backend(self) -> Backend:
        if self._backend is None:
            self._backend = NtfyBackend.from_config(self._load_config())
        return self._backend

    @property
    def theme(self) -> Theme:
        if self._theme is None:
            self._theme = validated_theme(optional_string(self._load_config(), "CLANKERS_THEME") or "neutral")
        return self._theme

    def _load_config(self) -> Config:
        if self._config is None:
            self._config = load_config(path=self._config_path, dotenv_path=self._dotenv_path)
        return self._config

    def send(self, event: Event) -> None:
        try:
            event = replace(event, theme=self.theme)
            logger.debug("reporting %s", event.to_string())
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
