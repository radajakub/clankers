"""Command-line wrapper for long-running commands."""

from __future__ import annotations

import argparse
import logging
import shlex
import subprocess
import sys
import time
from collections.abc import Sequence
from importlib import metadata

from clankers.config import ConfigError
from clankers.core import Clanker
from clankers.models import Event


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

    for action, help_text in (("rogerroger", "send a success notification"), ("uhoh", "send a failure notification")):
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

    clanker = Clanker(config_path=args.config, dotenv_path=args.dotenv)
    try:
        # Build the backend before the command runs, so a broken configuration fails early.
        clanker.backend
    except (ConfigError, ValueError) as exc:
        print(f"clankers: {exc}", file=sys.stderr)
        return 2

    if args.action == "engage":
        return _engage(clanker, command, args.message)

    if args.action == "rogerroger":
        clanker.rogerroger(args.message)
    else:
        clanker.uhoh(args.message)
    return 0


def _engage(clanker: Clanker, command: list[str], message: str | None) -> int:
    exit_code, error, duration = _run(command)
    clanker.send(Event.from_exit_code(message or shlex.join(command), duration, exit_code, error))
    return _shell_exit_code(exit_code)


def _command(arguments: list[str]) -> list[str]:
    return arguments[1:] if arguments[:1] == ["--"] else arguments


def _run(command: list[str]) -> tuple[int, OSError | None, float]:
    started_at = time.monotonic()
    error: OSError | None = None
    try:
        exit_code = subprocess.run(command, check=False).returncode
    except OSError as exc:
        exit_code, error = 127, exc
        print(f"clankers: could not run {command[0]!r}: {exc}", file=sys.stderr)
    return exit_code, error, time.monotonic() - started_at


def _shell_exit_code(return_code: int) -> int:
    return 128 - return_code if return_code < 0 else return_code


def _version() -> str:
    try:
        return metadata.version("clankers")
    except metadata.PackageNotFoundError:
        return "unknown"


if __name__ == "__main__":
    raise SystemExit(main())
