"""Schemas HTTP: cámaras / dispositivos IoT."""

from __future__ import annotations

from pydantic import BaseModel, Field

from rally.models.camera import Camera


class CameraCreate(BaseModel):
    """Alta de dispositivo en el registro (lo usan Movilidad / EAAB)."""

    dispositivo_id: str
    mac: str
    ip: str
    localizacion_x: float = Field(ge=0, le=100)
    localizacion_y: float = Field(ge=0, le=100)
    barrio: str
    upz: str = ""
    tipo: str = "fija"
    ubicacion: str = ""
    punto_critico_id: str | None = None
    fuente: str = "movilidad"


class CameraResponse(Camera):
    pass


class CameraIngestRequest(BaseModel):
    """Push de la cámara IoT al servidor (heartbeat + metadatos de frame)."""

    dispositivo_id: str
    mac: str | None = None
    ip: str | None = None
    estado: str = "activa"
    bateria_pct: float | None = Field(default=None, ge=0, le=100)
    frame_ref: str | None = None


class CameraIngestResponse(BaseModel):
    status: str
    dispositivo_id: str
    registrado: bool
    firewall: bool
