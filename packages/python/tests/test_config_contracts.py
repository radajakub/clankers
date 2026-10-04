from __future__ import annotations

import json
from pathlib import Path

import pytest

from clankers.config import load_config

PACKAGE = Path(__file__).resolve().parents[1]
CONTRACTS = PACKAGE / "contracts" / "configuration.json"
if not CONTRACTS.is_file():
    CONTRACTS = PACKAGE.parent.parent / "contracts" / "configuration.json"


@pytest.mark.parametrize("case", json.loads(CONTRACTS.read_text()), ids=lambda case: case["name"])
def test_configuration_matches_shared_contract(case: dict, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config_path = tmp_path / "config.toml"
    dotenv_path = tmp_path / ".env"
    if "toml" in case:
        config_path.write_text(case["toml"])
    if "dotenv" in case:
        dotenv_path.write_text(case["dotenv"])
    for key, value in case["env"].items():
        monkeypatch.setenv(key, value)

    assert load_config(path=config_path, dotenv_path=dotenv_path, env=case["env"]) == case["expected"]
