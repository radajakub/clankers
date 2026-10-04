from __future__ import annotations

import argparse
import json
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def shared_version(root: Path = ROOT) -> str:
    python = tomllib.loads((root / "packages/python/pyproject.toml").read_text())["project"]["version"]
    node = json.loads((root / "packages/nodejs/package.json").read_text())["version"]
    if python != node:
        raise ValueError(f"package versions differ: Python {python}, Node.js {node}")
    python_lock = tomllib.loads((root / "packages/python/uv.lock").read_text())
    locked_python = [package["version"] for package in python_lock["package"] if package["name"] == "clankers"]
    node_lock = json.loads((root / "packages/nodejs/package-lock.json").read_text())
    if locked_python != [python] or node_lock["version"] != node or node_lock["packages"][""]["version"] != node:
        raise ValueError("package lockfiles do not match the shared version")
    return python


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", help="also check the release tag, e.g. v3.1.0")
    args = parser.parse_args()
    try:
        version = shared_version()
        if args.tag is not None and args.tag != f"v{version}":
            raise ValueError(f"tag {args.tag} does not match shared version v{version}")
    except (ValueError, KeyError, OSError) as error:
        parser.exit(1, f"clankers: {error}\n")
    print(f"Both packages and lockfiles use {version}")


if __name__ == "__main__":
    main()
