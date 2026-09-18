# clankers

Small Python library to automatically send notifications using ntfy service

## Development

```bash
uv sync --group dev
make check   # ruff lint + format check + prettier
make fix     # autofix and reformat
make test    # pytest
make build   # wheel + sdist into dist/, validated with twine
```

## Releasing

`make release VERSION=1.2.0` bumps the version in `pyproject.toml`, opens a dated section in
`CHANGELOG.md`, commits, tags `v1.2.0`, pushes, and publishes a GitHub Release. The Release event
triggers `.github/workflows/publish.yml`, which builds and uploads to PyPI via Trusted Publishing.

Describe changes under `## [Unreleased]` in `CHANGELOG.md` before releasing — that section becomes
the release notes.

One-time setup on [pypi.org](https://pypi.org/manage/account/publishing/): add a trusted publisher
for project `clankers` with owner `radajakub`, repository `clankers`, workflow `publish.yml` and
environment `pypi`.
