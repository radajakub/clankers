# clankers

Get an ntfy notification when a long-running command or Python task finishes.

## Configuration

Set the ntfy server and topic with environment variables:

```bash
export NTFY_URL="https://ntfy.example.com"
export NTFY_TOPIC="default"
export NTFY_TOKEN="tk_your_private_access_token"
```

The same variables can live in a `.env` file in your project directory:

```dotenv
NTFY_URL=https://ntfy.example.com
NTFY_TOPIC=default
NTFY_TOKEN=tk_your_private_access_token
```

Both `NTFY_URL` and `NTFY_TOPIC` are required; clankers does not provide deployment defaults in
code. You can instead create
`~/.config/clankers/config.toml` (or `$XDG_CONFIG_HOME/clankers/config.toml`):

```toml
[ntfy]
url = "https://ntfy.example.com"
topic = "default"
token = "tk_your_private_access_token"
```

The loader returns normalized key/value pairs such as `NTFY_URL`; each backend selects and validates
its own settings. Sources are merged in this order of priority:

1. `.env`
2. process environment variables (only those prefixed `NTFY_`)
3. `~/.config/clankers/config.toml`

Settings themselves never come from the command line — only the files they live in do. Clankers
searches for `.env` from the working directory upward; use `--dotenv` to select one directly, and
`--config` to select a different TOML file.

## CLI

Prefix an arbitrary command with `clankers engage`:

```bash
clankers engage uv run pytest
clankers engage --config ./config.toml uv run train.py
clankers engage -m "nightly training" -- uv run train.py --epochs 100
```

Clankers' own flags must come before the command; everything after the first non-flag argument (or
after `--`) belongs to the wrapped command. The wrapped command keeps its standard input and output.
Clankers reports its duration and result, then returns the command's exit code. Without `--message`
the report is the command line itself. An unreachable notification server is silently ignored.

Send a notification on its own — at the end of a shell script, or from a Makefile:

```bash
clankers rogerroger -m "deploy finished"
clankers uhoh -m "deploy failed"
```

`clankers --version` prints the installed version. Delivery problems are reported on stderr —
a rejected or unreachable server never changes the exit code — and `-v` logs every file clankers
reads and every request it makes:

```console
$ clankers rogerroger -m "deploy finished" -v
clankers: reading .env file /home/you/project/.env
clankers: configuration provides NTFY_TOKEN, NTFY_TOPIC, NTFY_URL
clankers: publishing to https://ntfy.example.com/deploys with a 10.0s timeout
clankers: ntfy rejected the notification: 403 Forbidden {"code":40301,"error":"forbidden"}
```

## Python

The same helper works as a context manager or decorator:

```python
import clankers

with clankers.Engage("Training"):
    train()


@clankers.engage("Training")
def train(): ...


@clankers.engage()  # the message defaults to the function name
async def evaluate(): ...
```

Normal completion sends success. An exception sends failure and is re-raised unchanged. Async
functions are supported as decorators as well. Configuration is read the first time a notification is
sent, so decorating a function never fails at import time; a missing configuration or an unreachable
ntfy server is logged and never affects the wrapped work.

Clankers logs through the standard `logging` module under the `clankers` logger: failed deliveries at
`WARNING`, every file read and request made at `DEBUG`.

```python
logging.getLogger("clankers").setLevel(logging.DEBUG)
```

Every entry point shares one lazily built backend, so the configuration files are read once per
process. Point it somewhere else — or hand it a ready backend — with `configure()`:

```python
clankers.configure(config_path="./clankers.toml")
```

For a process that reports to more than one topic, build clankers of your own; each one owns its
backend and offers the same three entry points:

```python
training = clankers.Clanker(dotenv_path="./training.env")

with training.engage("Epoch 1"):
    ...

training.rogerroger("Checkpoint uploaded")
```

`clankers.Engage`, `engage`, `rogerroger` and `uhoh` always report through the shared clanker; every
configuration option lives on `Clanker` and `configure()`.

For work clankers does not wrap itself, send a notification by hand:

```python
clankers.rogerroger("Checkpoint uploaded")
clankers.uhoh("Validation loss diverged", duration=4200)
```

Both accept the same `config_path=` / `dotenv_path=` / `backend=` keywords and, like everything else,
only warn when the notification cannot be delivered.

## Development

```bash
uv sync --group dev
make check   # ruff lint + format check + prettier
make fix     # autofix and reformat
make test    # pytest
make build   # wheel + sdist into dist/, validated with twine
```

## Releasing

`make release VERSION=0.1.0` runs `scripts/release.py`, which bumps the version in `pyproject.toml`,
opens a dated section in `CHANGELOG.md`, commits, tags `v0.1.0`, pushes, and publishes a GitHub
Release. The Release event triggers `.github/workflows/publish.yml`, which builds and uploads to PyPI
via Trusted Publishing. It refuses to run unless you are on `master` with a clean tree in sync with
origin and the tag is unused.

Use `make release-dry-run VERSION=0.1.0` first to print every step without changing anything.

Describe changes under `## [Unreleased]` in `CHANGELOG.md` before releasing — that section becomes
the release notes.

One-time setup on [pypi.org](https://pypi.org/manage/account/publishing/): add a trusted publisher
for project `clankers` with owner `radajakub`, repository `clankers`, workflow `publish.yml` and
environment `pypi`.
