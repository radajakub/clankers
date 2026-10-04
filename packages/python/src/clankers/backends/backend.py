from typing import Protocol

from clankers.core.models import Event


class Backend(Protocol):
    def send(self, event: Event) -> None: ...
