from __future__ import annotations

import logging
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

import pytest
import requests

from clankers.backends.ntfy import NtfyBackend
from clankers.core.models import Event


class Response:
    status_code = 200
    closed = False

    def __enter__(self) -> Response:
        return self

    def __exit__(self, *args: object) -> None:
        self.closed = True
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
    assert captured["allow_redirects"] is False
    assert captured["stream"] is True
    assert captured["headers"] == {
        "Authorization": "Bearer secret-token",
        "User-Agent": "clankers",
        "Content-Type": "text/plain; charset=utf-8",
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

    assert headers == [{"User-Agent": "clankers", "Content-Type": "text/plain; charset=utf-8"}]


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


def test_rejection_is_logged_without_reading_response_secrets(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    class Rejected(Response):
        status_code = 403

        @property
        def text(self) -> str:
            pytest.fail("server response bodies must not be read or logged")

    response = Rejected()
    monkeypatch.setattr("clankers.backends.ntfy.requests.post", lambda url, **kwargs: response)

    with caplog.at_level(logging.WARNING, logger="clankers.backends.ntfy"):
        NtfyBackend("https://ntfy.example.com", "jobs").send(Event.rogerroger("job finished", 1))

    assert "ntfy rejected the notification: 403" in caplog.text
    assert response.closed


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


@pytest.mark.parametrize("timeout", [float("nan"), float("inf"), float("-inf"), True, "3"])
def test_rejects_unusable_direct_timeouts(timeout: Any) -> None:
    with pytest.raises(ValueError, match="timeout"):
        NtfyBackend("https://ntfy.sh", "jobs", timeout=timeout)


@pytest.mark.parametrize("topic", [0, False, [], {}])
def test_rejects_non_string_topics(topic: Any) -> None:
    with pytest.raises(ValueError, match="NTFY_TOPIC"):
        NtfyBackend("https://ntfy.sh", topic=topic)


@pytest.mark.parametrize("timeout", ["0", "-1", "nan", "inf", "2147483.648"])
def test_validates_timeouts_from_configuration(timeout: str) -> None:
    with pytest.raises(ValueError, match="timeout"):
        NtfyBackend.from_config({"NTFY_URL": "https://ntfy.sh", "NTFY_TOPIC": "jobs", "NTFY_TIMEOUT": timeout})


@pytest.mark.parametrize("status", [301, 302, 303, 307, 308])
def test_redirect_is_rejected_without_a_second_request(status: int, caplog: pytest.LogCaptureFixture) -> None:
    received: list[str] = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            received.append(self.path)
            self.send_response(status)
            self.send_header("Location", "/redirected")
            self.send_header("Content-Length", "0")
            self.end_headers()

        def do_GET(self) -> None:
            self.do_POST()

        def log_message(self, format: str, *args: object) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
    thread.start()
    try:
        with caplog.at_level(logging.DEBUG, logger="clankers.backends.ntfy"):
            NtfyBackend(f"http://127.0.0.1:{server.server_port}", "jobs", timeout=1).send(Event.rogerroger("Work"))
        assert received == ["/jobs"]
        assert f"ntfy rejected the notification: {status}" in caplog.text
        assert "accepted" not in caplog.text
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def test_network_errors_do_not_log_exception_secrets(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    def offline(*args: object, **kwargs: object) -> None:
        raise requests.ConnectionError("secret-token")

    monkeypatch.setattr("clankers.backends.ntfy.requests.post", offline)
    NtfyBackend("https://ntfy.sh", "jobs", token="secret-token").send(Event.rogerroger("Work"))

    assert "could not reach ntfy" in caplog.text
    assert "secret-token" not in caplog.text
