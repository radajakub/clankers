"""Command-line wrapper for long-running commands."""

from __future__ import annotations

import argparse
import logging
import shlex
import signal
import subprocess
import sys
import threading
import time
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from importlib import metadata
from typing import cast

from clankers.core.clanker import Clanker
from clankers.core.models import Event, Status

MANUAL_ACTIONS: dict[Status, str] = {
    "rogerroger": "send a success notification",
    "blastthem": "send a neutral notification",
    "uhoh": "send a failure notification",
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="clankers",
        description="Notifications for long-running work.",
    )
    parser.add_argument("--version", action="version", version=f"clankers {_version()}")
    actions = parser.add_subparsers(dest="action", required=True)

    engage_parser = actions.add_parser("engage", parents=[_settings_parser()], help="run a command and notify when it finishes")
    engage_parser.add_argument("-m", "--message", help="what to report instead of the command line")
    engage_parser.add_argument(
        "command",
        nargs=argparse.REMAINDER,
        help="command and arguments to run, optionally preceded by --",
    )

    for action, help_text in MANUAL_ACTIONS.items():
        manual_parser = actions.add_parser(action, parents=[_settings_parser()], help=help_text)
        manual_parser.add_argument("-m", "--message", required=True, help="what to report")

    return parser


def _settings_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--config", help="path to config.toml")
    parser.add_argument("--dotenv", help="path to a .env file (defaults to searching from the current directory)")
    parser.add_argument("-v", "--verbose", action="store_true", help="log what clankers reads and sends")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.WARNING, format="clankers: %(message)s")
    if args.verbose:
        logging.getLogger("clankers").setLevel(logging.DEBUG)

    command = _command(args.command) if args.action == "engage" else []
    if args.action == "engage" and not command:
        parser.error("a command is required")
    if args.message is not None and not args.message.strip():
        parser.error("message cannot be empty")

    clanker = Clanker(config_path=args.config, dotenv_path=args.dotenv)
    try:
        # Build the backend and theme before the command runs, so a broken configuration fails early.
        clanker.backend
        clanker.theme
    except ValueError as exc:
        print(f"clankers: {exc}", file=sys.stderr)
        return 2

    if args.action == "engage":
        return _engage(clanker, command, args.message)

    clanker.notify(cast(Status, args.action), args.message)
    return 0


def _engage(clanker: Clanker, command: list[str], message: str | None) -> int:
    exit_code, error, duration = _run(command)
    clanker.send(Event.from_exit_code(message or shlex.join(command), duration, exit_code, error))
    return _shell_exit_code(exit_code)


def _command(arguments: list[str]) -> list[str]:
    return arguments[1:] if arguments[:1] == ["--"] else arguments


def _run(command: list[str]) -> tuple[int, OSError | None, float]:
    started_at = time.monotonic()
    try:
        process = subprocess.Popen(command)
    except OSError as exc:
        print(f"clankers: could not run {command[0]!r}: {exc}", file=sys.stderr)
        return 127, exc, time.monotonic() - started_at
    with _forward_signals(process):
        exit_code = process.wait()
    return exit_code, None, time.monotonic() - started_at


@contextmanager
def _forward_signals(process: subprocess.Popen[bytes]) -> Iterator[None]:
    # Let the command decide how to stop, so it is not orphaned and its result is still reported.
    if threading.current_thread() is not threading.main_thread():
        yield
        return
    signals = (signal.SIGINT, signal.SIGTERM)
    previous = {signum: signal.signal(signum, lambda signum, _frame: process.send_signal(signum)) for signum in signals}
    try:
        yield
    finally:
        for signum, handler in previous.items():
            signal.signal(signum, handler)


def _shell_exit_code(return_code: int) -> int:
    return 128 - return_code if return_code < 0 else return_code


def _version() -> str:
    try:
        return metadata.version("clankers")
    except metadata.PackageNotFoundError:
        return "unknown"


if __name__ == "__main__":
    raise SystemExit(main())
