from __future__ import annotations

import sys
from pathlib import Path

import pytest

from clankers import cli
from clankers.core.models import Event


class RecordingBackend:
    events: list[Event] = []
    config: dict[str, object] = {}

    @classmethod
    def from_config(cls, config: dict[str, object]) -> RecordingBackend:
        cls.config = config
        return cls()

    def send(self, event: Event) -> None:
        self.events.append(event)


@pytest.fixture(autouse=True)
def isolate_cli_config(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    RecordingBackend.events.clear()
    RecordingBackend.config = {}
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.chdir(tmp_path)


@pytest.fixture
def backend(monkeypatch: pytest.MonkeyPatch) -> type[RecordingBackend]:
    monkeypatch.setattr("clankers.core.clanker.NtfyBackend", RecordingBackend)
    return RecordingBackend


def test_engage_returns_command_exit_code_and_reports_success(backend: type[RecordingBackend]) -> None:
    exit_code = cli.main(["engage", sys.executable, "-c", "raise SystemExit(0)"])

    assert exit_code == 0
    [event] = backend.events
    assert event.status == "rogerroger"
    assert event.message.endswith("raise SystemExit(0)'")
    assert not hasattr(event, "topic")


def test_engage_preserves_failure_exit_code(backend: type[RecordingBackend]) -> None:
    exit_code = cli.main(["engage", sys.executable, "-c", "raise SystemExit(7)"])

    assert exit_code == 7
    assert backend.events[0].status == "uhoh"
    assert backend.events[0].message.endswith("(exit code 7)")


def test_engage_uses_127_when_command_cannot_start(backend: type[RecordingBackend]) -> None:
    exit_code = cli.main(["engage", "/definitely/not/a/command"])

    assert exit_code == 127
    assert "(exit code 127)" in backend.events[0].message
    assert "FileNotFoundError" in backend.events[0].message


def test_engage_reports_a_custom_message(backend: type[RecordingBackend]) -> None:
    cli.main(["engage", "-m", "nightly training", "--", sys.executable, "-c", "raise SystemExit(1)"])

    assert backend.events[0].message == "nightly training (exit code 1)"


def test_engage_separates_its_flags_from_the_command(backend: type[RecordingBackend]) -> None:
    exit_code = cli.main(["engage", "--", sys.executable, "-c", "import sys; sys.exit(len(sys.argv) - 1)"])

    assert exit_code == 0
    assert backend.events[0].status == "rogerroger"


def test_manual_notifications_report_every_status(backend: type[RecordingBackend]) -> None:
    assert cli.main(["rogerroger", "-m", "deploy finished"]) == 0
    assert cli.main(["blastthem", "-m", "deploy started"]) == 0
    assert cli.main(["uhoh", "--message", "deploy failed"]) == 0

    assert [(event.status, event.message, event.duration) for event in backend.events] == [
        ("rogerroger", "deploy finished", None),
        ("blastthem", "deploy started", None),
        ("uhoh", "deploy failed", None),
    ]


def test_manual_notifications_require_a_message(backend: type[RecordingBackend]) -> None:
    with pytest.raises(SystemExit) as failure:
        cli.main(["rogerroger"])

    assert failure.value.code == 2


def test_cli_passes_loaded_values_to_backend(backend: type[RecordingBackend], tmp_path: Path) -> None:
    dotenv_path = tmp_path / "notifications.env"
    dotenv_path.write_text("NTFY_URL=https://ntfy.example\nNTFY_TOPIC=tests\nNTFY_TOKEN=private\n")

    cli.main(["engage", "--dotenv", str(dotenv_path), sys.executable, "-c", "pass"])

    assert backend.config["NTFY_URL"] == "https://ntfy.example"
    assert backend.config["NTFY_TOPIC"] == "tests"
    assert backend.config["NTFY_TOKEN"] == "private"


def test_cli_prefers_the_dotenv_over_the_environment(backend: type[RecordingBackend], monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("NTFY_TOPIC", "environment-topic")
    dotenv_path = tmp_path / "notifications.env"
    dotenv_path.write_text("NTFY_TOPIC=dotenv-topic\nNTFY_TOKEN=dotenv-token\n")

    cli.main(["rogerroger", "-m", "done", "--dotenv", str(dotenv_path)])

    assert backend.config["NTFY_TOPIC"] == "dotenv-topic"
    assert backend.config["NTFY_TOKEN"] == "dotenv-token"


def test_cli_reports_unusable_configuration(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    for key in ("NTFY_URL", "NTFY_TOPIC"):
        monkeypatch.delenv(key, raising=False)

    exit_code = cli.main(["engage", sys.executable, "-c", "pass"])

    assert exit_code == 2
    assert "NTFY_URL" in capsys.readouterr().err


def test_version_is_reported(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exit_info:
        cli.main(["--version"])

    assert exit_info.value.code == 0
    assert capsys.readouterr().out.startswith("clankers ")


def test_signal_return_code_uses_shell_convention() -> None:
    assert cli._shell_exit_code(-15) == 143
