"""Implementación en memoria del repositorio de detecciones.

El estado vive en memoria y se sincroniza con el JSON que escribe el modelo
(``data/live/detecciones.json``): ese archivo es la fuente del YOLO y lo que
consume la web visual.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from rally.models.detection import Detection
from rally.repositories.detection_repo import DetectionRepository
from rally.utils.datetime_utils import parse_iso


class MemoryDetectionRepository(DetectionRepository):
    def __init__(self, seed_path: Path | None = None) -> None:
        self._items: dict[str, Detection] = {}
        self._file: Path | None = seed_path
        if seed_path and seed_path.exists():
            self.sync_from_file()

    def sync_from_file(self) -> int:
        """Merge de los eventos nuevos del JSON del modelo. Devuelve cuántos entraron."""
        if self._file is None or not self._file.exists():
            return 0
        try:
            data = json.loads(self._file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return 0
        rows = data.get("detecciones", data) if isinstance(data, dict) else data
        nuevos = 0
        for row in rows:
            det = Detection(**row)
            if det.evento_id not in self._items:
                nuevos += 1
            self._items[det.evento_id] = det
        return nuevos

    def list(self) -> list[Detection]:
        self.sync_from_file()
        return sorted(self._items.values(), key=lambda d: d.timestamp, reverse=True)

    def get(self, key: str) -> Detection | None:
        self.sync_from_file()
        return self._items.get(key)

    def save(self, item: Detection) -> Detection:
        self._items[item.evento_id] = item
        return item

    def delete(self, key: str) -> bool:
        return self._items.pop(key, None) is not None

    def find_by_point(self, punto_critico_id: str) -> list[Detection]:
        return [d for d in self.list() if d.punto_critico_id == punto_critico_id]

    def find_since(self, since: datetime) -> list[Detection]:
        return [d for d in self.list() if parse_iso(d.timestamp) >= since]

    def purge_older_than(self, cutoff: datetime) -> int:
        self.sync_from_file()
        stale = [k for k, d in self._items.items() if parse_iso(d.timestamp) < cutoff]
        for k in stale:
            del self._items[k]
        return len(stale)
