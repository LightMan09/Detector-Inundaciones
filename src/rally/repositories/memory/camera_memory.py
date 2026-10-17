"""Implementación en memoria del repositorio de cámaras.

El registro (firewall IoT) empieza vacío y se llena en runtime con
``POST /api/cameras``; se persiste en ``data/live/camaras.json``.
"""

from __future__ import annotations

import json
from pathlib import Path

from rally.models.camera import Camera
from rally.repositories.camera_repo import CameraRepository


class MemoryCameraRepository(CameraRepository):
    def __init__(self, seed_path: Path | None = None) -> None:
        self._items: dict[str, Camera] = {}
        self._raw: list[dict] = []
        self._file: Path | None = seed_path
        if seed_path and seed_path.exists():
            self.load_seed(seed_path)

    def load_seed(self, seed_path: Path) -> None:
        data = json.loads(seed_path.read_text(encoding="utf-8"))
        self._raw = list(data)
        for row in data:
            cam = Camera(**row).validated()
            self._items[cam.dispositivo_id] = cam

    def _persist(self) -> None:
        if self._file is None:
            return
        self._file.parent.mkdir(parents=True, exist_ok=True)
        self._file.write_text(
            json.dumps(self._raw, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def list(self) -> list[Camera]:
        return list(self._items.values())

    def get(self, key: str) -> Camera | None:
        return self._items.get(key)

    def save(self, item: Camera) -> Camera:
        item = item.validated()
        self._items[item.dispositivo_id] = item
        raw = item.model_dump()
        self._raw = [r for r in self._raw if r.get("dispositivo_id") != item.dispositivo_id]
        self._raw.append(raw)
        self._persist()
        return item

    def delete(self, key: str) -> bool:
        self._raw = [r for r in self._raw if r.get("dispositivo_id") != key]
        self._persist()
        return self._items.pop(key, None) is not None

    def find_by_mac_or_ip(self, mac: str | None, ip: str | None) -> Camera | None:
        mac = (mac or "").upper()
        for cam in self._items.values():
            if mac and cam.mac.upper() == mac:
                return cam
            if ip and cam.ip == ip:
                return cam
        return None

    def find_by_barrio(self, barrio: str) -> list[Camera]:
        needle = barrio.strip().lower()
        return [c for c in self._items.values() if needle in c.barrio.lower()]

    def load_raw(self) -> list[dict]:
        return list(self._raw)
