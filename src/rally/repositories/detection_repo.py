"""Repositorio de detecciones."""

from __future__ import annotations

from abc import abstractmethod
from datetime import datetime

from rally.models.detection import Detection
from rally.repositories.base import Repository


class DetectionRepository(Repository[Detection]):
    @abstractmethod
    def find_by_point(self, punto_critico_id: str) -> list[Detection]: ...

    @abstractmethod
    def find_since(self, since: datetime) -> list[Detection]: ...

    @abstractmethod
    def purge_older_than(self, cutoff: datetime) -> int: ...
