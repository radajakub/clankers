.PHONY: lint format check fix test build clean release release-dry-run

# Check lint and formatting (same checks as CI)
lint:
	uv run ruff check .
	uv run ruff format --check .
	npx --yes prettier@3.9.6 --check .

# Alias for lint
check: lint

# Autofix lint issues and reformat
format:
	uv run ruff check --fix .
	uv run ruff format .
	npx --yes prettier@3.9.6 --write .

# Alias for format
fix: format

test:
	uv run --group dev pytest -q

# Build wheel and sdist into dist/, then validate the metadata PyPI will see
build: clean
	uv build
	uvx twine check dist/*

clean:
	rm -rf dist build

# Cut a release: make release VERSION=0.1.0
# Bumps the version, tags it, and publishes a GitHub Release, which triggers the PyPI upload.
release:
	@test -n "$(VERSION)" || (echo "usage: make release VERSION=0.1.0" >&2; exit 1)
	uv run python scripts/release.py $(VERSION)

# Print every step of a release without changing anything
release-dry-run:
	@test -n "$(VERSION)" || (echo "usage: make release-dry-run VERSION=0.1.0" >&2; exit 1)
	uv run python scripts/release.py $(VERSION) --dry-run
