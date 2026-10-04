from __future__ import annotations

import json
from pathlib import Path

import pytest

from clankers.core.models import Event

PACKAGE = Path(__file__).resolve().parents[1]
CONTRACTS = PACKAGE / "contracts" / "notification-format.json"
if not CONTRACTS.is_file():
    CONTRACTS = PACKAGE.parent.parent / "contracts" / "notification-format.json"


@pytest.mark.parametrize("case", json.loads(CONTRACTS.read_text(encoding="utf-8")))
def test_notification_format_matches_shared_contract(case: dict[str, object]) -> None:
    values = dict(case)
    expected = values.pop("expected")

    assert Event(**values).to_string() == expected
