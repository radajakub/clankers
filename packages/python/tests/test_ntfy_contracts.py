from __future__ import annotations

import json
from pathlib import Path

import pytest

from clankers.backends.ntfy import NtfyBackend

PACKAGE = Path(__file__).resolve().parents[1]
CONTRACTS = PACKAGE / "contracts" / "ntfy-validation.json"
if not CONTRACTS.is_file():
    CONTRACTS = PACKAGE.parent.parent / "contracts" / "ntfy-validation.json"


@pytest.mark.parametrize("case", json.loads(CONTRACTS.read_text()), ids=lambda case: case["name"])
def test_backend_validation_matches_shared_contract(case: dict) -> None:
    options = {"url": case["url"], "topic": case["topic"]}
    if "timeoutSeconds" in case:
        options["timeout"] = case["timeoutSeconds"]
    if case["valid"]:
        NtfyBackend(**options)
    else:
        with pytest.raises(ValueError, match=case["field"]):
            NtfyBackend(**options)
