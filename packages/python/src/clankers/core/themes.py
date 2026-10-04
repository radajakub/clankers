from __future__ import annotations

from typing import Literal

Status = Literal["rogerroger", "blastthem", "uhoh"]
Theme = Literal["neutral", "starwars"]

_LABELS: dict[Theme, dict[Status, str]] = {
    "neutral": {
        "rogerroger": "Done",
        "blastthem": "Info",
        "uhoh": "Failed",
    },
    "starwars": {
        "rogerroger": "Roger, roger",
        "blastthem": "Blast them!",
        "uhoh": "Uh-oh",
    },
}


def label(theme: Theme, status: Status) -> str:
    return _LABELS[validated_theme(theme)][status]


def validated_theme(theme: str) -> Theme:
    if theme not in _LABELS:
        raise ValueError(f"unknown theme {theme!r}, expected one of {', '.join(_LABELS)}")
    return theme
