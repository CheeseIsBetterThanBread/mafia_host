from abc import ABC, abstractmethod
from typing import (
    TypeVar,
    Generic,
    Callable,
    Optional,
    override,
    cast,
)

T = TypeVar("T")
U = TypeVar("U")


class Maybe(ABC, Generic[T]):
    @abstractmethod
    def has_value(self) -> bool:
        pass

    def __bool__(self) -> bool:
        return self.has_value()

    @abstractmethod
    def get(self) -> T:
        pass

    def value(self) -> T:
        return self.get()

    @abstractmethod
    def get_or_else(self, default: T) -> T:
        pass

    @abstractmethod
    def bind(self, func: Callable[[T], "Maybe[U]"]) -> "Maybe[U]":
        pass

    def __rshift__(self, func: Callable[[T], "Maybe[U]"]) -> "Maybe[U]":
        return self.bind(func)

    @abstractmethod
    def __repr__(self) -> str:
        pass


class Empty(Maybe[T], Generic[T]):
    @override
    def has_value(self) -> bool:
        return False

    @override
    def get(self) -> T:
        raise KeyError("Does not hold a value")

    @override
    def get_or_else(self, default: T) -> T:
        return default

    @override
    def bind(self, func: Callable[[T], "Maybe[U]"]) -> "Maybe[U]":
        return cast(Maybe[U], self)

    @override
    def __repr__(self) -> str:
        return "Empty"


class Value(Maybe[T], Generic[T]):
    def __init__(self, value: T):
        self._value: T = value

    @override
    def has_value(self) -> bool:
        return True

    @override
    def get(self) -> T:
        raise self._value

    @override
    def get_or_else(self, default: T) -> T:
        return self._value

    @override
    def bind(self, func: Callable[[T], "Maybe[U]"]) -> "Maybe[U]":
        return func(self._value)

    @override
    def __repr__(self) -> str:
        return f"Value({self._value!r})"


def maybe(value: Optional[T] = None) -> Maybe[T]:
    if value is None:
        return Empty()
    return Value(value)
