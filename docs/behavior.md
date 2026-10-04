# Shared behavior

Python and Node.js are sibling implementations of Clankers. Neither implementation is the
source of truth for the other; this contract and the fixtures under `contracts/` describe
behavior that both packages must verify.

## Notifications

The statuses are `rogerroger` (success), `blastthem` (information), and `uhoh` (failure).
The default `neutral` theme labels them `Done`, `Info`, and `Failed`. The `starwars` theme
labels them `Roger, roger`, `Blast them!`, and `Uh-oh`. Unknown themes are rejected.

Notification text has the form `(hostname) [duration] Label: message`. The duration and its
preceding space are omitted when no duration is supplied. Empty or whitespace-only messages
are rejected; otherwise the original message is preserved.

Durations are measured in seconds, rounded to the nearest whole second with ties to even,
and clamped to zero. They render as `Xs`, `Xm Ys`, or `Xh Ym Zs`.

## Delivery

Publish UTF-8 text with HTTP POST to the configured server and topic. The server and topic
are required configuration; there is no implicit deployment default. The token is optional
and, when present, is sent as bearer authentication. The default delivery timeout is ten seconds.
Tokens must not appear in diagnostics.

Delivery failures are logged and must not change the result of wrapped work. Notifications
are best-effort, not a durable queue, and are not automatically retried.

## Wrapped work

Announce the start unless disabled, then report success or failure with elapsed duration.
Preserve the original result or thrown error. Evaluate message builders at the relevant
phase; an invalid or failing builder falls back to the original phase message.
Timing and reporting state belong to each invocation so concurrent work remains independent.

## Configuration and language APIs

The common keys are `NTFY_URL`, `NTFY_TOPIC`, `NTFY_TOKEN`, `NTFY_TIMEOUT` (seconds), and
`CLANKERS_THEME`. Explicit options and file-loading support are documented per package.
Python currently merges TOML, process environment, then `.env`, with later sources taking
precedence. Node.js configuration support and precedence must be documented before release.

Python supports context managers and decorators. Node.js will support awaitable notification
methods and callback-based task wrappers. These APIs may differ while preserving this contract.

## Keeping implementations aligned

A shared behavior change updates this document, the affected fixtures, and both implementations
in the same change. Each package runs the shared fixtures in its test suite. A change that
only affects a language-specific API uses that package's tests.

The Node.js implementation is pending. Once added, CI must validate both implementations
before a shared behavior change can be merged. Package versioning and paired release policy
will be established with the release tooling.
