"""Repositorio de cámaras (registro de dispositivos)."""

from __future__ import annotations

from abc import abstractmethod

from rally.models.camera import Camera
from rally.repositories.base import Repository


class CameraRepository(Repository[Camera]):
    """Contrato del registro de cámaras que alimenta el firewall IoT."""

    @abstractmethod
    def find_by_mac_or_ip(self, mac: str | None, ip: str | None) -> Camera | None: ...

    @abstractmethod
    def find_by_barrio(self, barrio: str) -> list[Camera]: ...

    @abstractmethod
    def load_raw(self) -> list[dict]: ...
