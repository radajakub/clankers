.PHONY: lint format check check-python fix test test-python build build-python clean release release-dry-run

# Check lint and formatting (same checks as CI)
lint: check-python
	npx --yes prettier@3.9.6 --check .

check-python:
	uv run --project packages/python ruff check --config packages/python/pyproject.toml packages/python scripts
	uv run --project packages/python ruff format --config packages/python/pyproject.toml --check packages/python scripts

# Alias for lint
check: lint

# Autofix lint issues and reformat
format:
	uv run --project packages/python ruff check --config packages/python/pyproject.toml --fix packages/python scripts
	uv run --project packages/python ruff format --config packages/python/pyproject.toml packages/python scripts
	npx --yes prettier@3.9.6 --write .

# Alias for format
fix: format

test: test-python

test-python:
	uv run --project packages/python --group dev pytest -q packages/python/tests

# Build wheel and sdist into dist/, then validate the metadata PyPI will see
build: build-python

build-python: clean
	uv build --project packages/python --out-dir dist
	uvx twine check dist/*

clean:
	rm -rf dist build

# Cut a release: make release VERSION=0.1.0
# Bumps the version, tags it, and publishes a GitHub Release, which triggers the PyPI upload.
release:
	@test -n "$(VERSION)" || (echo "usage: make release VERSION=0.1.0" >&2; exit 1)
	uv run --project packages/python python scripts/release.py $(VERSION)

# Print every step of a release without changing anything
release-dry-run:
	@test -n "$(VERSION)" || (echo "usage: make release-dry-run VERSION=0.1.0" >&2; exit 1)
	uv run --project packages/python python scripts/release.py $(VERSION) --dry-run
