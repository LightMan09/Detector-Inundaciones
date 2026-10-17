"""Entidades de dominio: zonas (UPZ y puntos críticos)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class CriticalPoint(BaseModel):
    """Punto georreferenciado de encharcamiento / sumidero tapado."""

    punto_id: str
    nombre: str
    upz: str
    barrio: str
    localizacion_x: float = Field(ge=0, le=100)
    localizacion_y: float = Field(ge=0, le=100)
    nivel_agua_cm: float = 0
    cobertura_basura_pct: float = 0
    riesgo: float = Field(default=0, ge=0, le=100)
    severidad: str = "leve"
    tipo_afectacion: str = "vial"
    repeticion_30d: int = 0
    lluvia_prevista_mm: float = 0
    barrios_afectados: list[str] = Field(default_factory=list)


class Zone(BaseModel):
    """UPZ de Engativá con su priorización operativa."""

    zona_id: str
    codigo: str
    nombre: str
    riesgo: float = Field(default=0, ge=0, le=100)
    severidad: str = "leve"
    estado_alerta: str = "verde"
    puntos: list[CriticalPoint] = Field(default_factory=list)
    barrios: list[str] = Field(default_factory=list)
    resumen: str = ""
