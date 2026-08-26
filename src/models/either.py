from abc import ABC, abstractmethod
from typing import (
    TypeVar,
    Generic,
    Callable,
    Any,
    Awaitable,
    override,
    cast,
)

from src.models.maybe import Maybe, maybe

L = TypeVar("L")
R = TypeVar("R")
R2 = TypeVar("R2")


class Either(ABC, Generic[L, R]):
    @abstractmethod
    def is_left(self) -> bool:
        pass

    @abstractmethod
    def is_right(self) -> bool:
        pass

    @abstractmethod
    def get_left(self) -> Maybe[L]:
        pass

    @abstractmethod
    def get_right(self) -> Maybe[R]:
        pass

    @abstractmethod
    def bind(self, func: Callable[[R], "Either[L, R2]"]) -> "Either[L, R2]":
        pass

    @abstractmethod
    async def async_bind(
        self, func: Callable[[R], Awaitable["Either[L, R2]"]]
    ) -> "Either[L, R2]":
        pass

    def __rshift__(self, func: Callable[[R], "Either[L, R2]"]) -> "Either[L, R2]":
        return self.bind(func)

    @abstractmethod
    def __repr__(self) -> str:
        pass


class Left(Either[L, R], Generic[L, R]):
    def __init__(self, value: L):
        self._value: L = value

    @override
    def is_left(self) -> bool:
        return True

    @override
    def is_right(self) -> bool:
        return False

    @override
    def get_left(self) -> Maybe[L]:
        return maybe(self._value)

    @override
    def get_right(self) -> Maybe[R]:
        return maybe()

    @override
    def bind(self, func: Callable[[R], "Either[L, R2]"]) -> "Either[L, R2]":
        return cast(Either[L, R2], self)

    @override
    async def async_bind(
        self, func: Callable[[R], Awaitable["Either[L, R2]"]]
    ) -> "Either[L, R2]":
        return cast(Either[L, R2], self)

    @override
    def __repr__(self) -> str:
        return f"Left({self._value!r})"


class Right(Either[L, R], Generic[L, R]):
    def __init__(self, value: R):
        self._value: R = value

    @override
    def is_left(self) -> bool:
        return False

    @override
    def is_right(self) -> bool:
        return True

    @override
    def get_left(self) -> Maybe[L]:
        return maybe()

    @override
    def get_right(self) -> Maybe[R]:
        return maybe(self._value)

    @override
    def bind(self, func: Callable[[R], "Either[L, R2]"]) -> "Either[L, R2]":
        return func(self._value)

    @override
    async def async_bind(
        self, func: Callable[[R], Awaitable["Either[L, R2]"]]
    ) -> "Either[L, R2]":
        result = await func(self._value)
        return result

    @override
    def __repr__(self) -> str:
        return f"Right({self._value!r})"


def left(value: L) -> Either[L, Any]:
    return Left(value)


def right(value: R) -> Either[Any, R]:
    return Right(value)
