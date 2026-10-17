"""Priorización de zonas y puntos críticos (mapa de riesgo).

Todo se deriva de las detecciones que escribe el modelo en
``data/live/detecciones.json``: no hay datos precargados.
"""

from __future__ import annotations

from rally.core.constants import SEVERITY_ALTO_MAX_CM, SEVERITY_MEDIO_MAX_CM
from rally.models.detection import Detection
from rally.models.zone import Zone
from rally.repositories.detection_repo import DetectionRepository
from rally.repositories.zone_repo import ZoneRepository
from rally.services.detection_service import DetectionService


class ZoneService:
    def __init__(self, zones: ZoneRepository, detections: DetectionRepository) -> None:
        self.zones = zones
        self.detections = detections
        self.detection_service = DetectionService(detections, zones)

    def sync(self) -> list[Detection]:
        """Deriva zonas y puntos críticos del JSON del modelo."""
        dets = self.detections.list()
        self.zones.derive_from(dets)
        repeticion_por_upz: dict[str, int] = {}
        for det in dets:
            clave = det.upz or "sin_asignar"
            repeticion_por_upz[clave] = repeticion_por_upz.get(clave, 0) + 1
        for point in self.zones.list_points():
            det = self.detections.get(point.punto_id)
            if det is None:
                continue
            point.repeticion_30d = repeticion_por_upz.get(det.upz or "sin_asignar", 1)
            point.riesgo = self.detection_service.risk_score(
                det, point.repeticion_30d, point.lluvia_prevista_mm
            )
            point.severidad = det.severity
            self.zones.save_point(point)
        for zone in self.zones.list():
            if zone.puntos:
                zone.riesgo = max(p.riesgo for p in zone.puntos)
        return dets

    def ranking(self) -> list[Zone]:
        self.sync()
        return self.zones.list()

    def critical_points(self, min_risk: float = 0) -> list:
        self.sync()
        return [p for p in self.zones.list_points() if p.riesgo >= min_risk]

    @staticmethod
    def alert_state(nivel_cm: float) -> str:
        if nivel_cm > SEVERITY_ALTO_MAX_CM:
            return "roja"
        if nivel_cm > SEVERITY_MEDIO_MAX_CM:
            return "naranja"
        if nivel_cm > 10:
            return "amarilla"
        return "verde"
