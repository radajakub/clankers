from __future__ import annotations

import json
from pathlib import Path

import pytest
import release
from versions import shared_version


def package_files(root: Path, python: str = "3.0.0", node: str = "3.0.0", locked: str = "3.0.0") -> None:
    python_dir = root / "packages/python"
    node_dir = root / "packages/nodejs"
    python_dir.mkdir(parents=True)
    node_dir.mkdir(parents=True)
    (python_dir / "pyproject.toml").write_text(f'[project]\nversion = "{python}"\n')
    (python_dir / "uv.lock").write_text(f'[[package]]\nname = "clankers"\nversion = "{locked}"\n')
    (node_dir / "package.json").write_text(json.dumps({"version": node}))
    (node_dir / "package-lock.json").write_text(json.dumps({"version": locked, "packages": {"": {"version": locked}}}))


def test_shared_version_checks_packages_and_lockfiles(tmp_path: Path) -> None:
    package_files(tmp_path)
    assert shared_version(tmp_path) == "3.0.0"


@pytest.mark.parametrize("python,node,locked", [("3.0.0", "3.1.0", "3.0.0"), ("3.0.0", "3.0.0", "2.0.0")])
def test_version_drift_is_rejected(tmp_path: Path, python: str, node: str, locked: str) -> None:
    package_files(tmp_path, python, node, locked)
    with pytest.raises(ValueError):
        shared_version(tmp_path)


def test_release_dry_run_updates_both_packages_without_executing_actions(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[tuple[str, ...], bool]] = []
    monkeypatch.setattr("sys.argv", ["release.py", "3.1.0", "--dry-run"])
    monkeypatch.setattr(release, "shared_version", lambda: "3.0.0")
    monkeypatch.setattr(release, "check_tools", lambda: None)
    monkeypatch.setattr(release, "check_repo", lambda tag: None)
    monkeypatch.setattr(release, "unreleased_notes", lambda: "Paired release")
    monkeypatch.setattr(release, "open_changelog_section", lambda version, dry_run: None)
    monkeypatch.setattr(release, "commit_and_tag", lambda tag, dry_run: None)
    monkeypatch.setattr(release, "execute", lambda *args, dry_run: calls.append((args, dry_run)))

    assert release.main() == 0
    assert all(dry_run for _, dry_run in calls)
    commands = [args for args, _ in calls]
    assert ("uv", "version", "--project", "packages/python", "3.1.0") in commands
    assert ("npm", "--prefix", "packages/nodejs", "version", "3.1.0", "--no-git-tag-version", "--ignore-scripts") in commands
    assert commands.index(("make", "test")) < commands.index(("make", "build"))


@pytest.mark.parametrize("version", ["3.0.0", "2.9.0", "3.1.0rc1", "03.1.0"])
def test_invalid_or_non_increasing_versions_fail_before_actions(monkeypatch: pytest.MonkeyPatch, version: str) -> None:
    monkeypatch.setattr("sys.argv", ["release.py", version])
    monkeypatch.setattr(release, "shared_version", lambda: "3.0.0")
    monkeypatch.setattr(release, "check_tools", lambda: pytest.fail("must fail before external actions"))
    assert release.main() == 1
