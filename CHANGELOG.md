# Changelog

All notable changes to this project are documented in this file. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Add `clankers engage` to wrap commands, preserve their exit status, and send completion
  notifications, with `--message` to report a label instead of the command line.
- Add `clankers rogerroger` and `clankers uhoh` to send a single notification from a shell, and
  `clankers --version`.
- Add `clankers.Engage` as a context manager and `clankers.engage` as a sync/async decorator whose
  message defaults to the decorated function's name.
- Add `clankers.rogerroger` and `clankers.uhoh` to send a notification for work that is not wrapped
  in a context manager or decorator.
- Add `clankers.Clanker`, a client that resolves its backend once and exposes the context manager,
  the decorator and the manual notifications; `clankers.configure` replaces the shared default.
- Report delivery problems through the `clankers` logger, including the status and body ntfy
  answered with; `clankers -v` logs every file read and request made.
- Add shared event modeling, TOML/environment configuration, and an ntfy backend.
- Support private ntfy servers using bearer tokens from `NTFY_TOKEN`, TOML, Python, or the CLI.
- Resolve configuration from `.env`, then `NTFY_` environment variables, then
  `~/.config/clankers/config.toml`; `--config` and `--dotenv` select the files.

## [0.0.0] - 2026-09-18

### Added

- Initial packaging: build with `uv build` and publish to PyPI from a GitHub Release.
