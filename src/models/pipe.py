from typing import TypeVar, Generic, Callable, Union, Awaitable, Any, cast
from src.models.either import Either

L = TypeVar("L")
R = TypeVar("R")
R2 = TypeVar("R2")


class Pipe(Generic[L, R]):
    def __init__(self, initial: Either[L, R]):
        self._initial: Either[L, R] = initial
        self._handlers: list[Callable] = []

    def __rshift__(
        self, func: Callable[[R], Union[Either[L, R2], Awaitable[Either[L, R2]]]]
    ) -> "Pipe[L, R2]":
        new_pipe = Pipe(self._initial)
        new_pipe._handlers = self._handlers.copy()
        new_pipe._handlers.append(func)
        return cast(Pipe[L, R2], new_pipe)

    async def execute(self) -> Either[L, R]:
        current: Either[L, Any] = self._initial

        for handler in self._handlers:
            if current.is_left:
                return current

            right_value = current.get_right().value()
            result = handler(right_value)

            if hasattr(result, "__await__"):
                current = await result
            else:
                current = result

        return current

    def __repr__(self) -> str:
        return f"Pipe(initial={self._initial!r}, handlers={len(self._handlers)})"
