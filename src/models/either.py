from abc import ABC, abstractmethod
from typing import (
    TypeVar,
    Generic,
    Callable,
    Optional,
    Union,
    Any,
    override,
    cast,
)

L = TypeVar("L")
L2 = TypeVar("L2")
R = TypeVar("R")
R2 = TypeVar("R2")
T = TypeVar("T")


class Either(ABC, Generic[L, R]):
    @abstractmethod
    def is_left(self) -> bool:
        pass

    @abstractmethod
    def is_right(self) -> bool:
        pass

    @abstractmethod
    def get_left(self) -> Optional[L]:
        pass

    @abstractmethod
    def get_right(self) -> Optional[R]:
        pass

    @abstractmethod
    def bind(self, func: Callable[[R], "Either[L, R2]"]) -> "Either[L, R2]":
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
    def get_left(self) -> Optional[L]:
        return self._value

    @override
    def get_right(self) -> Optional[R]:
        return None

    @override
    def bind(self, func: Callable[[R], "Either[L, R2]"]) -> "Either[L, R2]":
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
    def get_left(self) -> Optional[L]:
        return None

    @override
    def get_right(self) -> Optional[R]:
        return self._value

    @override
    def bind(self, func: Callable[[R], "Either[L, R2]"]) -> "Either[L, R2]":
        return func(self._value)

    @override
    def __repr__(self) -> str:
        return f"Right({self._value!r})"


def left(value: L) -> Either[L, Any]:
    return Left(value)


def right(value: R) -> Either[Any, R]:
    return Right(value)
