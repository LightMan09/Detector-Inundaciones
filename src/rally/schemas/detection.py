"""Schemas HTTP: detecciones que llegan del docker del modelo."""

from __future__ import annotations

from pydantic import BaseModel

from rally.models.detection import Detection, DetectionBatch


class DetectionCreate(DetectionBatch):
    """POST /api/detections - payload del contenedor YOLO."""


class DetectionResponse(Detection):
    pass


class DetectionListResponse(BaseModel):
    total: int
    items: list[Detection]


class DetectionAck(BaseModel):
    status: str = "accepted"
    recibidas: int
    criticas: int = 0
    alertas_generadas: int = 0
