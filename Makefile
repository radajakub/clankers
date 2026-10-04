.PHONY: lint format check check-python check-nodejs check-versions fix test test-python test-nodejs build build-python build-nodejs clean release release-dry-run

# Check lint and formatting (same checks as CI)
lint: check-python check-nodejs check-versions
	npx --yes prettier@3.9.6 --check .

check-python:
	uv run --project packages/python ruff check --config packages/python/pyproject.toml packages/python scripts
	uv run --project packages/python ruff format --config packages/python/pyproject.toml --check packages/python scripts

check-nodejs:
	npm run check --prefix packages/nodejs

check-versions:
	uv run --project packages/python python scripts/versions.py

# Alias for lint
check: lint

# Autofix lint issues and reformat
format:
	uv run --project packages/python ruff check --config packages/python/pyproject.toml --fix packages/python scripts
	uv run --project packages/python ruff format --config packages/python/pyproject.toml packages/python scripts
	npx --yes prettier@3.9.6 --write .

# Alias for format
fix: format

test: test-python test-nodejs

test-python:
	uv run --project packages/python --group dev pytest -q packages/python/tests scripts/test_release.py

test-nodejs:
	npm test --prefix packages/nodejs

# Build wheel and sdist into dist/, then validate the metadata PyPI will see
build: clean
	$(MAKE) build-python build-nodejs

build-python:
	uv build --project packages/python --out-dir dist/python
	uvx twine check dist/python/*

build-nodejs:
	npm run build --prefix packages/nodejs
	mkdir -p dist/nodejs
	npm pack ./packages/nodejs --ignore-scripts --pack-destination dist/nodejs
	node packages/nodejs/scripts/smoke.mjs dist/nodejs/*.tgz

clean:
	rm -rf dist build

# Cut a release: make release VERSION=0.1.0
# Bumps both versions and publishes a GitHub Release, which triggers PyPI and npm uploads.
release:
	@test -n "$(VERSION)" || (echo "usage: make release VERSION=0.1.0" >&2; exit 1)
	uv run --project packages/python python scripts/release.py $(VERSION)

# Print every step of a release without changing anything
release-dry-run:
	@test -n "$(VERSION)" || (echo "usage: make release-dry-run VERSION=0.1.0" >&2; exit 1)
	uv run --project packages/python python scripts/release.py $(VERSION) --dry-run
