"""Schemas HTTP comunes."""

from __future__ import annotations

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    app: str
    version: str
    devices_registered: int
    yolo_model: str = "no_conectado"


class ErrorResponse(BaseModel):
    error: str
    detail: str


class MessageResponse(BaseModel):
    status: str
    detail: str = ""
