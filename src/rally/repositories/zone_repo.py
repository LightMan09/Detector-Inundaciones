"""Repositorio de zonas / puntos críticos."""

from __future__ import annotations

from abc import abstractmethod

from rally.models.zone import CriticalPoint, Zone
from rally.repositories.base import Repository


class ZoneRepository(Repository[Zone]):
    @abstractmethod
    def list_points(self) -> list[CriticalPoint]: ...

    @abstractmethod
    def get_point(self, punto_id: str) -> CriticalPoint | None: ...

    @abstractmethod
    def save_point(self, point: CriticalPoint) -> CriticalPoint: ...
