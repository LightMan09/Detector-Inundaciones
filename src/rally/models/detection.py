"""Entidades de dominio: detecciones del docker del modelo YOLO."""

from __future__ import annotations

from pydantic import BaseModel, Field

from rally.core.constants import (
    SEVERITY_ALTO_MAX_CM,
    SEVERITY_LEVE_MAX_CM,
    SEVERITY_MEDIO_MAX_CM,
    TRASH_COVER_HIGH_PCT,
)
from rally.utils.datetime_utils import utcnow


class Detection(BaseModel):
    """Lo que envía el modelo de deep learning (Docker 2) por JSON.

    ``origen`` permite distinguir el flujo: cámara fija (movilidad), camión de
    succión (limpieza en ruta) o reporte ciudadano validado por IA.
    """

    evento_id: str
    dispositivo_id: str
    timestamp: str = Field(default_factory=lambda: utcnow().isoformat())
    punto_critico_id: str | None = None
    upz: str = ""
    barrio: str = ""
    clase: str = "agua"  # agua | basura | limpia | sin_deteccion
    clase_modelo: str = ""  # clase cruda del modelo: limpia | tapada | con_agua
    estado: str = ""  # estado del monitor: INUNDADA | DRENANDO | BASURA | LIMPIA | SIN_DET
    confianza: float = Field(default=0.5, ge=0, le=1)
    nivel_agua_cm: float = Field(default=0, ge=0)
    cobertura_basura_pct: float = Field(default=0, ge=0, le=100)
    drena_lento: bool = False
    tiempo_drenaje_s: float | None = None
    lluvia_mm_h: float = 0
    # El modelo no tiene geolocalización exacta: posición aleatoria sobre el mapa (0-100)
    localizacion_x: float = Field(default=50, ge=0, le=100)
    localizacion_y: float = Field(default=50, ge=0, le=100)
    origen: str = "yolo_docker"
    frame_ref: str | None = None

    @property
    def severity(self) -> str:
        if self.nivel_agua_cm > SEVERITY_ALTO_MAX_CM:
            return "critico"
        if self.nivel_agua_cm > SEVERITY_MEDIO_MAX_CM:
            return "alto"
        if self.nivel_agua_cm > SEVERITY_LEVE_MAX_CM:
            return "medio"
        if self.cobertura_basura_pct >= TRASH_COVER_HIGH_PCT:
            return "medio"
        return "leve"

    @property
    def implies_clog(self) -> bool:
        """Infiere taponamiento interno: llovió y el agua no baja."""
        return self.drena_lento or (
            self.lluvia_mm_h > 0 and self.nivel_agua_cm > SEVERITY_LEVE_MAX_CM
        )


class DetectionBatch(BaseModel):
    """Lote de detecciones que envía el docker del modelo."""

    dispositivo_id: str
    detections: list[Detection] = Field(default_factory=list)
