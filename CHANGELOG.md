# Changelog

All notable changes to this project are documented in this file. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [3.0.1] - 2026-10-04

### Added

- Add the TypeScript/Node.js package `@radajakub/clankers`, with asynchronous notifications,
  task reporting, neutral and Star Wars themes, shared TOML/dotenv/environment configuration, and
  injectable backends and logging. Publish CommonJS, ESM, and TypeScript declarations.
- Verify shared configuration and notification-format fixtures in both packages and check package/lockfile versions in CI.
- Build and publish both packages from one shared version and GitHub Release, with retry support.
- Add the npm `clankers` executable with the same actions and configuration options as Python,
  shared CLI fixtures, command exit-code preservation, and installed-executable validation.

### Changed

- Place Python and Node.js in sibling package directories, with shared documentation and root commands.
- Release commands now validate and bump both packages; paired releases use stable `X.Y.Z` versions.
- Align ntfy URL, topic, and timeout validation in Python and Node.js with shared validation fixtures.
  Both reject redirects, send UTF-8 plain-text headers, and log status-only rejection diagnostics.

## [3.0.0] - 2026-10-04

### Added

- Add a configurable theme for notification text. The default `neutral` theme labels notifications
  `Done`, `Info` and `Failed`; `theme = "starwars"` under `[clankers]` in `config.toml`, or
  `CLANKERS_THEME=starwars`, restores `Roger, roger`, `Blast them!` and `Uh-oh`. `Clanker` and
  `configure` take `theme=`. Names in code and on the command line are unchanged.
- Collect process environment variables prefixed `CLANKERS_` alongside `NTFY_`.
- Add `Event.is_success`, `Event.is_info` and `Event.is_failure` to check an event's status without
  comparing strings.

### Changed

- Notifications use the neutral labels unless the Star Wars theme is configured.
- A `Clanker` reads its configuration once for both the backend and the theme, so one built with a
  `backend=` now reads the configuration files the first time it sends, to find its theme.

## [2.0.0] - 2026-09-19

### Added

- Add `blastthem`, a neutral notification level alongside `rogerroger` and `uhoh`, on `Clanker`, as
  a module-level function, as a CLI action, and inside a context manager.
- Announce the start of every context manager and decorated function with a `blastthem`
  notification; `announce=False` reports only the outcome. `clankers engage` is unchanged.
- Build the message of each phase when it is sent: `Engage` takes `start`, `success` and `failure`
  callables that read the surrounding scope, with `failure` receiving the exception. A builder that
  fails or returns nothing is logged and the plain message is sent instead.
- Add `Engage.rogerroger`, `Engage.blastthem` and `Engage.uhoh` so a block can send extra
  notifications while it runs; the report the block sends when it exits is unaffected.
- Add `Clanker.notify` and `Event.of` to send any level without picking a named helper.

### Changed

- Replace `Event.success` with `Event.status`, one of `rogerroger`, `blastthem` or `uhoh`.
- Split the package by responsibility: `clankers.core` holds the event model, the `Clanker` and the
  context manager, `clankers.default` owns the shared clanker and the module-level notifications,
  and `clankers.decorators` the decorator. Importing from `clankers` itself is unchanged.
- Separate the decorator from the context manager: `clankers.engage` is now the decorator and
  `clankers.Engage` the context manager, and both take an optional `clanker=`. `Engage` no longer
  decorates, and its message is required.

### Removed

- Remove `Event.from_exception`; a context manager describes its own failures and `describe` renders
  an exception for anything else.
- Remove `Clanker.engage`; name the clanker where the work is wrapped instead, with
  `clankers.Engage(..., clanker=yours)` or `@clankers.engage(..., clanker=yours)`.
- Remove `clankers.utils`; `required_string` and `optional_string` moved to `clankers.config`.

## [1.0.1] - 2026-09-18

- Relax Python version to 3.12

## [1.0.0] - 2026-09-18

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
