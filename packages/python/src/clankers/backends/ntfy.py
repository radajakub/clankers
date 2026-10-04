from __future__ import annotations

import logging
import math
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from urllib.parse import urlsplit

import requests

from clankers.backends.backend import Backend
from clankers.config import optional_string, required_string
from clankers.core.models import Event

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class NtfyBackend(Backend):
    url: str  # url of the NTFY backend
    topic: str | None = None  # topic for the NTFY backend
    timeout: float = 10.0  # timeout in seconds when unreachable
    token: str | None = field(default=None, repr=False)  # private-server access token

    def _match_url(self) -> bool:
        return re.match(r"^https?://", self.url, re.IGNORECASE) is not None

    def _search_url(self) -> bool:
        return re.search(r"[\s\\?#]", self.url) is not None

    def _valid_topic(self) -> bool:
        if self.topic is None:
            return True
        if not isinstance(self.topic, str):
            return False

        return self.topic == "" or re.fullmatch(r"[A-Za-z0-9_-]+", self.topic) is not None

    def _valid_timeout(self) -> bool:
        if isinstance(self.timeout, bool) or not isinstance(self.timeout, (int, float)):
            return False

        return 0 < self.timeout <= 2_147_483_647 / 1000 and math.isfinite(self.timeout)

    def __post_init__(self) -> None:
        try:
            if not isinstance(self.url, str) or not self._match_url() or self._search_url():
                raise ValueError

            url = urlsplit(self.url)
            if not url.hostname or url.username is not None or url.password is not None:
                raise ValueError

            # Accessing port also validates its syntax and range.
            url.port
        except ValueError:
            raise ValueError("NTFY_URL must be HTTP or HTTPS without credentials, query, fragment, whitespace, or backslashes") from None

        if not self._valid_topic():
            raise ValueError("NTFY_TOPIC must contain only letters, numbers, underscores, or hyphens")

        if not self._valid_timeout():
            raise ValueError("notification timeout must be positive, finite, and no greater than 2147483.647 seconds")

    @classmethod
    def from_config(cls, config: Mapping[str, object]) -> NtfyBackend:
        url = required_string(config, "NTFY_URL")
        topic = required_string(config, "NTFY_TOPIC")
        token = optional_string(config, "NTFY_TOKEN")
        timeout_value = optional_string(config, "NTFY_TIMEOUT")

        if timeout_value is None:
            return cls(url=url, topic=topic, token=token)

        # Plain decimals only, so both packages accept the same values (float() also takes "1_0" or "1e3").
        if re.fullmatch(r"\s*([0-9]+(\.[0-9]*)?|\.[0-9]+)\s*", timeout_value) is None:
            raise ValueError("NTFY_TIMEOUT must be a decimal number of seconds")

        return cls(url=url, topic=topic, timeout=float(timeout_value), token=token)

    def _build_headers(self) -> dict[str, str]:
        headers = {"User-Agent": "clankers", "Content-Type": "text/plain; charset=utf-8"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _build_url(self, topic: str) -> str:
        return f"{self.url.rstrip('/')}/{topic}"

    def send(self, event: Event) -> None:
        if not self.topic:
            logger.warning("no ntfy topic configured, dropping notification")
            return

        url = self._build_url(self.topic)
        logger.debug("publishing to %s with a %ss timeout", url, self.timeout)
        try:
            with requests.post(
                url,
                data=event.to_string().encode(),
                headers=self._build_headers(),
                timeout=self.timeout,
                allow_redirects=False,
                stream=True,
            ) as response:
                if not 200 <= response.status_code < 300:
                    logger.warning("ntfy rejected the notification: %s", response.status_code)
                else:
                    logger.debug("ntfy accepted the notification with status %s", response.status_code)
        except requests.RequestException:
            logger.warning("could not reach ntfy at %s", url)
