from __future__ import annotations

import pytest

from clankers.core.themes import label, validated_theme


@pytest.mark.parametrize(
    ("theme", "status", "text"),
    [
        ("neutral", "rogerroger", "Done"),
        ("neutral", "blastthem", "Info"),
        ("neutral", "uhoh", "Failed"),
        ("starwars", "rogerroger", "Roger, roger"),
        ("starwars", "blastthem", "Blast them!"),
        ("starwars", "uhoh", "Uh-oh"),
    ],
)
def test_every_theme_labels_every_status(theme: str, status: str, text: str) -> None:
    assert label(theme, status) == text  # type: ignore[arg-type]


def test_label_rejects_an_unknown_theme() -> None:
    with pytest.raises(ValueError, match="unknown theme"):
        label("startrek", "rogerroger")  # type: ignore[arg-type]


def test_unknown_theme_is_rejected() -> None:
    with pytest.raises(ValueError, match="unknown theme 'startrek', expected one of neutral, starwars"):
        validated_theme("startrek")
