from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass, field

import requests

from clankers.backends.backend import Backend
from clankers.models import Event
from clankers.utils import optional_string, required_string

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class NtfyBackend(Backend):
    url: str  # url of the NTFY backend
    topic: str | None = None  # topic for the NTFY backend
    timeout: float = 10.0  # timeout in seconds when unreachable
    token: str | None = field(default=None, repr=False)  # private-server access token

    @classmethod
    def from_config(cls, config: Mapping[str, object]) -> NtfyBackend:
        url = required_string(config, "NTFY_URL")
        topic = required_string(config, "NTFY_TOPIC")
        token = optional_string(config, "NTFY_TOKEN")
        timeout_value = optional_string(config, "NTFY_TIMEOUT")

        if timeout_value is None:
            return cls(url=url, topic=topic, token=token)

        try:
            timeout = float(timeout_value)
        except (TypeError, ValueError) as exc:
            raise ValueError("NTFY_TIMEOUT must be a number") from exc

        return cls(url=url, topic=topic, timeout=timeout, token=token)

    def _build_headers(self) -> dict[str, str]:
        headers = {"User-Agent": "clankers"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _build_url(self, topic: str) -> str:
        return f"{self.url.rstrip('/')}/{topic}"

    def send(self, event: Event) -> None:
        if not self.topic:
            logger.warning("no ntfy topic configured, dropping notification: %s", event.message)
            return

        url = self._build_url(self.topic)
        logger.debug("publishing to %s with a %ss timeout", url, self.timeout)
        try:
            response = requests.post(
                url,
                data=event.to_string().encode(),
                headers=self._build_headers(),
                timeout=self.timeout,
            )
            response.raise_for_status()
        except requests.HTTPError as exc:
            # Notifications are optional and must never affect the wrapped work.
            logger.warning("ntfy rejected the notification: %s", _describe_response(exc.response))
        except requests.RequestException as exc:
            logger.warning("could not reach ntfy at %s: %s", url, exc)
        else:
            logger.debug("ntfy accepted the notification with status %s", response.status_code)


def _describe_response(response: requests.Response | None) -> str:
    if response is None:
        return "no response"
    return f"{response.status_code} {response.reason} {response.text.strip()[:200]}".strip()
