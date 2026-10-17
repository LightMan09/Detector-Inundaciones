"""Lógica de negocio sobre detecciones del modelo.

Reglas del ciclo "Detectar / Priorizar":
- si llovió y el agua no baja en un punto -> se infiere taponamiento interno
  sin necesidad de sensores dentro de la tubería;
- cada detección se cruza con el pronóstico de lluvia y la repetición histórica
  del punto para calcular su prioridad.
"""

from __future__ import annotations

import logging

from rally.core.constants import RISK_WEIGHTS, SLOW_DRAIN_SECONDS, TRASH_COVER_HIGH_PCT
from rally.models.detection import Detection
from rally.repositories.detection_repo import DetectionRepository
from rally.repositories.zone_repo import ZoneRepository
from rally.utils.datetime_utils import hours_ago, utcnow

logger = logging.getLogger(__name__)


class DetectionService:
    def __init__(self, detections: DetectionRepository, zones: ZoneRepository) -> None:
        self.detections = detections
        self.zones = zones

    def ingest(self, payload: list[Detection]) -> dict:
        """Guarda detecciones del docker del modelo y devuelve un resumen."""
        criticas = 0
        for det in payload:
            det.timestamp = det.timestamp or utcnow().isoformat()
            if det.severity in ("critico", "alto"):
                criticas += 1
            self.detections.save(det)
            self._update_point(det)
        logger.info("Ingesta: %d detecciones (%d críticas)", len(payload), criticas)
        return {"recibidas": len(payload), "criticas": criticas}

    def _update_point(self, det: Detection) -> None:
        if not det.punto_critico_id:
            return
        point = self.zones.get_point(det.punto_critico_id)
        if point is None:
            return
        point.nivel_agua_cm = max(point.nivel_agua_cm, det.nivel_agua_cm)
        point.cobertura_basura_pct = max(point.cobertura_basura_pct, det.cobertura_basura_pct)
        point.riesgo = self.risk_score(det, point.repeticion_30d, point.lluvia_prevista_mm)
        point.severidad = det.severity
        self.zones.save_point(point)

    def risk_score(
        self, det: Detection, repeticion_30d: int = 0, lluvia_prevista_mm: float = 0
    ) -> float:
        """Score 0-100: nivel de agua, basura, repetición y lluvia prevista.

        La severidad (umbrales duros de cm) fija un suelo mínimo para no
        subestimar un punto con histórico corto.
        """
        nivel = min(det.nivel_agua_cm / 50.0, 1.0)
        basura = min(det.cobertura_basura_pct / 100.0, 1.0)
        repeticion = min(repeticion_30d / 10.0, 1.0)
        lluvia = min(lluvia_prevista_mm / 40.0, 1.0)
        score = (
            nivel * RISK_WEIGHTS["nivel_agua"]
            + basura * RISK_WEIGHTS["basura"]
            + repeticion * RISK_WEIGHTS["repeticion"]
            + lluvia * RISK_WEIGHTS["lluvia"]
        ) * 100
        floor = {"critico": 80, "alto": 60, "medio": 40, "leve": 0}[det.severity]
        return round(max(score, float(floor)), 1)

    def infer_clog(self, det: Detection) -> bool:
        """Detección indirecta de taponamiento (sin sensores en la tubería)."""
        if det.drena_lento:
            return True
        if det.tiempo_drenaje_s is not None and det.tiempo_drenaje_s > SLOW_DRAIN_SECONDS:
            return True
        return det.lluvia_mm_h > 0 and det.nivel_agua_cm > 10

    def needs_trash_pickup(self, det: Detection) -> bool:
        return det.cobertura_basura_pct >= TRASH_COVER_HIGH_PCT

    def summary(self, window_hours: int = 24) -> dict:
        recent = self.detections.find_since(hours_ago(window_hours))
        return {
            "ventana_h": window_hours,
            "total": len(recent),
            "criticas": sum(1 for d in recent if d.severity == "critico"),
            "taponamientos": sum(1 for d in recent if self.infer_clog(d)),
            "con_basura": sum(1 for d in recent if self.needs_trash_pickup(d)),
            "nivel_max_cm": max((d.nivel_agua_cm for d in recent), default=0),
        }
