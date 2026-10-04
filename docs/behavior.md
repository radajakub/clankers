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

Both backends reject HTTP redirects and accept only 2xx responses. Requests identify the
client as `clankers` and use `Content-Type: text/plain; charset=utf-8`. Rejection diagnostics
include the HTTP status without logging response bodies; connection diagnostics do not include
exception details. Response bodies are closed or cancelled after receiving the status.

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
Both implementations read `~/.config/clankers/config.toml`, or
`$XDG_CONFIG_HOME/clankers/config.toml`, and discover the nearest `.env` from the working directory
upward. Explicit paths select different files. They merge TOML, process environment, then `.env`,
with later sources taking precedence. Empty environment and `.env` values do not override settings.
Both verify `contracts/configuration.json`, including normalized TOML keys and dotenv interpolation.
Use TOML 1.0 syntax for files shared with Python's parser.

Node.js constructor options override this merged configuration. Both backends validate
absolute HTTP(S) URLs with a hostname, without credentials, query strings, fragments,
whitespace, or backslashes. Nonempty topics contain only ASCII letters, numbers, underscores,
and hyphens. Timeouts are finite, positive, and at most 2,147,483.647 seconds (2,147,483,647 ms).
Both run `contracts/ntfy-validation.json` to verify these rules. Python timeout arguments use
seconds; Node.js timeout arguments use milliseconds.
Backend configuration values from files are strings, including TOML timeout values.

Python supports context managers and decorators. Node.js supports awaitable notification
methods and callback-based task wrappers. These APIs may differ while preserving this contract.

## Keeping implementations aligned

A shared behavior change updates this document, the affected fixtures, and both implementations
in the same change. Each package runs the shared fixtures in its test suite. A change that
only affects a language-specific API uses that package's tests.

CI validates both packages and rejects version drift, including lockfiles. Both packages use
one shared version, one root changelog, and one `vX.Y.Z` release tag. Every release publishes
both packages, including changes that affect only one language. See [releasing](releasing.md).

Both packages provide a `clankers` CLI with `engage`, `rogerroger`, `blastthem`, and `uhoh`.
CLI options include `--config`, `--dotenv`, `--message` / `-m`, and `--verbose` / `-v`.
Both verify `contracts/cli.json`. `engage` runs commands directly with inherited input and
output, sends one completion notification, and preserves their exit code. Invalid configuration
fails before work starts with exit code 2; commands that cannot start return 127. On Unix,
signal termination uses shell exit codes (128 plus the signal number); the notification reports
the original negative signal code. Operating-system error descriptions may differ.

The Node.js library's task wrapper always returns a promise, including for synchronous work.
File-parser and command-line-parser edge cases may differ between language-specific parsers.
