# Clankers

Get an ntfy notification when long-running work finishes.
Clankers supports private ntfy servers and public services through a configurable server URL,
topic, and optional access token.

## Packages

| Language             | Package                                      | Status                                    |
| -------------------- | -------------------------------------------- | ----------------------------------------- |
| Python               | [Python package](packages/python/README.md)  | Published on PyPI as `clankers`           |
| Node.js / TypeScript | [Node.js package](packages/nodejs/README.md) | Implementation and npm publishing planned |

The packages follow a [shared behavior contract](docs/behavior.md). Language-specific APIs
are documented in each package. Shared fixtures under `contracts/` keep observable behavior aligned.

## Development

Python development dependencies can be installed with `uv sync --project packages/python --group dev`.

```bash
make check        # Python lint and repository formatting checks
make test         # Python tests, including shared behavior fixtures
make build        # Python wheel and source distribution, validated with twine
```

Each command also has a Python-specific target: `check-python`, `test-python`, and `build-python`.
Node.js targets will join the aggregate commands when its implementation is added.

## Releases

The existing Python release process remains available through `make release VERSION=X.Y.Z`
and `make release-dry-run VERSION=X.Y.Z`. It uses the root `CHANGELOG.md`, updates Python
metadata, commits, tags, pushes, and creates a GitHub Release that triggers PyPI publishing.
Do not run it just to validate local changes.

The joint versioning and npm release process will be added after the Node.js implementation.
