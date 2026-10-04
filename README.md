# Clankers

Get an ntfy notification when long-running work finishes.
Use your private ntfy server or a public service with a configurable URL, topic, and optional token.

## Packages

| Language             | Package                                                  | Documentation                                         |
| -------------------- | -------------------------------------------------------- | ----------------------------------------------------- |
| Python               | `clankers` on PyPI                                       | [Python guide](packages/python/README.md)             |
| Node.js / TypeScript | `@radajakub/clankers` on npm (first publication pending) | [Node.js and NestJS guide](packages/nodejs/README.md) |

The packages follow a [shared behavior contract](docs/behavior.md), use the same version,
and are released together. Language-specific APIs suit their runtime; shared fixtures under
`contracts/` keep notification formatting aligned.

Python:

```python
import clankers

with clankers.Engage("Backup"):
    upload_backup()
```

Node.js:

```ts
import { engage } from "@radajakub/clankers";

await engage("Backup", async () => uploadBackup());
```

Both examples read `NTFY_URL` and `NTFY_TOPIC` from configuration. `NTFY_TOKEN` is optional.
Both read the same TOML file and `.env` files, with the same source precedence.
Node.js also accepts explicit constructor options.

Both packages provide the `clankers` command with `engage`, `rogerroger`, `blastthem`, and
`uhoh`. See the [Python CLI guide](packages/python/README.md#cli) or
[npm CLI guide](packages/nodejs/README.md#command-line) for arguments and examples.

## Development

```bash
uv sync --project packages/python --group dev
npm ci --prefix packages/nodejs
make check        # Python lint, TypeScript checks, formatting, and shared versions
make test         # Both packages and release-tool tests
make build        # Validated Python distributions and npm archive
```

Target one package with `check-python`, `check-nodejs`, `test-python`, `test-nodejs`,
`build-python`, or `build-nodejs`. `make check-versions` checks both package manifests and lockfiles.
Select `packages/python/.venv` as your editor's Python environment after running `uv sync`.
The root `pyrightconfig.json` makes the Python source discoverable when opening the whole repository.
Python artifacts go to `dist/python/` and the npm archive to `dist/nodejs/`.
Node.js archive validation installs it into a temporary project and checks CommonJS, ESM,
TypeScript consumers, and the CLI. The [Node.js development guide](packages/nodejs/README.md#development-and-releases)
also shows how to run the local archive before publishing.

CI groups lint/type checks, tests, and package validation into one job per language,
with Node.js checked on versions 22 and 24. A shared job checks versions and repository formatting.

## Releases

Both packages use one stable `X.Y.Z` version, one root `CHANGELOG.md`, and one `vX.Y.Z` tag.
`make release VERSION=X.Y.Z` validates both packages, updates both manifests and lockfiles,
commits, tags, pushes, and creates a GitHub Release. The publish workflow validates and builds
both packages before publishing to PyPI and npm using Trusted Publishing.

See [release setup and recovery](docs/releasing.md), including the first npm publication.
