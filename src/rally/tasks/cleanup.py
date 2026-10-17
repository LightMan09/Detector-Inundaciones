"""Tareas asíncronas: limpieza de detecciones viejas."""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

from rally.repositories.detection_repo import DetectionRepository
from rally.utils.datetime_utils import utcnow

logger = logging.getLogger(__name__)


class CleanupTask:
    def __init__(
        self, detections: DetectionRepository, ttl_hours: int = 48, interval_s: float = 3600
    ) -> None:
        self.detections = detections
        self.ttl_hours = ttl_hours
        self.interval_s = interval_s
        self._task: asyncio.Task | None = None

    async def _loop(self) -> None:
        while True:
            cutoff = utcnow() - timedelta(hours=self.ttl_hours)
            removed = self.detections.purge_older_than(cutoff)
            if removed:
                logger.info("Cleanup: %d detecciones eliminadas (>%dh)", removed, self.ttl_hours)
            await asyncio.sleep(self.interval_s)

    def start(self) -> None:
        self._task = asyncio.get_event_loop().create_task(self._loop())

    def stop(self) -> None:
        if self._task:
            self._task.cancel()
