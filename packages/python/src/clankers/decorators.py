from __future__ import annotations

import inspect
from functools import wraps
from typing import Any, Callable, Coroutine, TypeVar, cast

from clankers.core.clanker import Clanker
from clankers.core.context import Engage

F = TypeVar("F", bound=Callable[..., Any])


def engage(message: str | None = None, *, clanker: Clanker | None = None) -> Callable[[F], F]:
    def decorate(func: F) -> F:
        label = message if message is not None else func.__qualname__

        if inspect.iscoroutinefunction(func):
            coroutine_func = cast(Callable[..., Coroutine[Any, Any, Any]], func)

            @wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                with Engage(label, clanker=clanker):
                    return await coroutine_func(*args, **kwargs)

            return cast(F, async_wrapper)

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            with Engage(label, clanker=clanker):
                return func(*args, **kwargs)

        return cast(F, wrapper)

    return decorate
