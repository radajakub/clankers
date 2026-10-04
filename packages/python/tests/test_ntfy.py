from __future__ import annotations

import logging
from typing import Any

import pytest
import requests

from clankers.backends.ntfy import NtfyBackend
from clankers.core.models import Event


class Response:
    status_code = 200

    def raise_for_status(self) -> None:
        return None


def test_sends_plain_text_publish_request_with_bearer_token(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    def fake_post(url: str, **kwargs: Any) -> Response:
        captured["url"] = url
        captured.update(kwargs)
        return Response()

    monkeypatch.setattr("clankers.backends.ntfy.requests.post", fake_post)
    event = Event.rogerroger("pytest", 134)

    backend = NtfyBackend("https://ntfy.example.com", "builds", timeout=3, token="secret-token")
    backend.send(event)

    assert captured["url"] == "https://ntfy.example.com/builds"
    assert captured["timeout"] == 3
    assert captured["headers"] == {
        "Authorization": "Bearer secret-token",
        "User-Agent": "clankers",
    }
    assert captured["data"] == event.to_string().encode()
    assert "secret-token" not in repr(backend)


def test_omits_authorization_header_without_token(monkeypatch: pytest.MonkeyPatch) -> None:
    headers: list[dict[str, str]] = []

    def fake_post(url: str, **kwargs: Any) -> Response:
        headers.append(kwargs["headers"])
        return Response()

    monkeypatch.setattr("clankers.backends.ntfy.requests.post", fake_post)
    NtfyBackend("https://ntfy.example.com", "jobs").send(Event(message="job finished", status="rogerroger", duration=0))

    assert headers == [{"User-Agent": "clankers"}]


def test_backend_topic_is_used_in_publish_url(monkeypatch: pytest.MonkeyPatch) -> None:
    urls: list[str] = []

    def fake_post(url: str, **kwargs: Any) -> Response:
        urls.append(url)
        return Response()

    monkeypatch.setattr("clankers.backends.ntfy.requests.post", fake_post)
    NtfyBackend("https://ntfy.example.com", "special").send(Event(message="job finished", status="rogerroger", duration=0))
    assert urls == ["https://ntfy.example.com/special"]


def test_missing_topic_is_a_silent_noop(monkeypatch: pytest.MonkeyPatch) -> None:
    def unexpected_post(*args: object, **kwargs: object) -> None:
        pytest.fail("an unconfigured backend must not make a request")

    monkeypatch.setattr("clankers.backends.ntfy.requests.post", unexpected_post)
    NtfyBackend("https://ntfy.example.com").send(Event(message="job finished", status="rogerroger", duration=0))


def test_unreachable_server_is_a_silent_noop(monkeypatch: pytest.MonkeyPatch) -> None:
    def offline(*args: object, **kwargs: object) -> None:
        raise requests.ConnectionError("offline")

    monkeypatch.setattr("clankers.backends.ntfy.requests.post", offline)
    NtfyBackend("https://ntfy.example.com", "jobs").send(Event(message="job finished", status="rogerroger", duration=0))


def test_builds_backend_from_its_own_configuration() -> None:
    backend = NtfyBackend.from_config(
        {
            "NTFY_URL": "https://ntfy.example.com",
            "NTFY_TOPIC": "builds",
            "NTFY_TOKEN": "secret-token",
            "NTFY_TIMEOUT": "3.5",
            "UNRELATED_VALUE": "ignored",
        }
    )

    assert backend.url == "https://ntfy.example.com"
    assert backend.topic == "builds"
    assert backend.timeout == 3.5
    assert "secret-token" not in repr(backend)


@pytest.mark.parametrize("key", ["NTFY_URL", "NTFY_TOPIC"])
def test_backend_requires_its_own_configuration(key: str) -> None:
    config = {"NTFY_URL": "https://ntfy.example.com", "NTFY_TOPIC": "builds"}
    del config[key]

    with pytest.raises(ValueError, match=key):
        NtfyBackend.from_config(config)


def test_failure_payload_has_compact_visible_status(monkeypatch: pytest.MonkeyPatch) -> None:
    payloads: list[bytes] = []

    def fake_post(url: str, **kwargs: Any) -> Response:
        payloads.append(kwargs["data"])
        return Response()

    monkeypatch.setattr("clankers.backends.ntfy.requests.post", fake_post)
    event = Event.uhoh("pytest failed with exit code 1", 38)

    NtfyBackend("https://ntfy.example.com", "builds").send(event)

    assert payloads == [event.to_string().encode()]


def test_rejection_is_logged_with_the_server_response(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    class Rejected:
        status_code = 403
        reason = "Forbidden"
        text = '{"code":40301,"error":"forbidden"}'

        def raise_for_status(self) -> None:
            raise requests.HTTPError(response=self)

    monkeypatch.setattr("clankers.backends.ntfy.requests.post", lambda url, **kwargs: Rejected())

    with caplog.at_level(logging.WARNING, logger="clankers.backends.ntfy"):
        NtfyBackend("https://ntfy.example.com", "jobs").send(Event.rogerroger("job finished", 1))

    assert "403 Forbidden" in caplog.text
    assert "forbidden" in caplog.text


def test_unreachable_server_is_logged(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    def offline(*args: object, **kwargs: object) -> None:
        raise requests.ConnectionError("offline")

    monkeypatch.setattr("clankers.backends.ntfy.requests.post", offline)

    with caplog.at_level(logging.WARNING, logger="clankers.backends.ntfy"):
        NtfyBackend("https://ntfy.example.com", "jobs").send(Event.rogerroger("job finished", 1))

    assert "could not reach ntfy at https://ntfy.example.com/jobs" in caplog.text


def test_missing_topic_is_logged(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING, logger="clankers.backends.ntfy"):
        NtfyBackend("https://ntfy.example.com").send(Event.rogerroger("job finished", 1))

    assert "no ntfy topic configured" in caplog.text
