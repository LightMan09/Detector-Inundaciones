"""Schemas HTTP: zonas, alertas y despacho."""

from __future__ import annotations

from pydantic import BaseModel, Field

from rally.models.zone import CriticalPoint, Zone


class ZoneResponse(Zone):
    pass


class CriticalPointResponse(CriticalPoint):
    pass


class ZoneRankingResponse(BaseModel):
    total: int
    items: list[Zone]


class AlertCreate(BaseModel):
    titulo: str
    severidad: str = "alto"
    upz: str = ""
    punto_critico_id: str | None = None
    detalle: str = ""


class AlertResponse(BaseModel):
    alerta_id: str
    titulo: str
    severidad: str
    upz: str
    punto_critico_id: str | None = None
    detalle: str = ""
    timestamp: str
    notificados: list[str] = Field(default_factory=list)


class DispatchOrder(BaseModel):
    orden_id: str
    camion_id: str
    punto_critico_id: str
    prioridad: int
    ruta: list[str] = Field(default_factory=list)
    accion: str = "presion-succion"
    estado: str = "asignada"
    distancia_estimada_km: float = 0


class DispatchResponse(BaseModel):
    generadas: int
    ordenes: list[DispatchOrder]
