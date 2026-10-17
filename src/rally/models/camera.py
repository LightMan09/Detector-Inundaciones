"""Entidad de dominio: cámara / dispositivo IoT del registro."""

from __future__ import annotations

from pydantic import BaseModel, Field

from rally.utils.validators import (
    validate_device_id,
    validate_ip,
    validate_mac,
    validate_map_position,
)


class Camera(BaseModel):
    """Dispositivo IoT (cámara fija, móvil o camión de succión).

    La IP y la MAC se leen del encabezado del push de la cámara al servidor;
    con eso se busca el resto de la información en el registro.
    """

    dispositivo_id: str
    mac: str
    ip: str
    localizacion_x: float = Field(ge=0, le=100, description="Posición % sobre el mapa de Engativá")
    localizacion_y: float = Field(ge=0, le=100)
    barrio: str
    upz: str = ""
    tipo: str = "fija"
    ubicacion: str = ""
    punto_critico_id: str | None = None
    estado: str = "activa"
    fuente: str = "movilidad"

    def validated(self) -> "Camera":
        validate_device_id(self.dispositivo_id)
        validate_mac(self.mac)
        validate_ip(self.ip)
        validate_map_position(self.localizacion_x, self.localizacion_y)
        return self

    @property
    def online(self) -> bool:
        return self.estado == "activa"
