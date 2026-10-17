"""Interfaz abstracta de acceso a datos."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

T = TypeVar("T")


class Repository(ABC, Generic[T]):
    """CRUD mínimo que implementan los repositorios en memoria y (a futuro) DB."""

    @abstractmethod
    def list(self) -> list[T]: ...

    @abstractmethod
    def get(self, key: str) -> T | None: ...

    @abstractmethod
    def save(self, item: T) -> T: ...

    @abstractmethod
    def delete(self, key: str) -> bool: ...
