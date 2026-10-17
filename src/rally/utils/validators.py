"""Validadores de campos del registro de cámaras y de detecciones."""

from __future__ import annotations

import re

from rally.core.exceptions import ValidationException

MAC_RE = re.compile(r"^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$")
IP_RE = re.compile(r"^\d{1,3}(\.\d{1,3}){3}$")
DEVICE_ID_RE = re.compile(r"^[a-z0-9_\-]{3,40}$", re.IGNORECASE)


def validate_mac(value: str) -> str:
    if not MAC_RE.match(value or ""):
        raise ValidationException(f"MAC inválida: {value!r}")
    return value.upper()


def validate_ip(value: str) -> str:
    if not IP_RE.match(value or ""):
        raise ValidationException(f"IP inválida: {value!r}")
    parts = [int(p) for p in value.split(".")]
    if any(p > 255 for p in parts):
        raise ValidationException(f"IP inválida: {value!r}")
    return value


def validate_device_id(value: str) -> str:
    if not DEVICE_ID_RE.match(value or ""):
        raise ValidationException(f"dispositivo_id inválido: {value!r}")
    return value


def validate_map_position(x: float, y: float) -> tuple[float, float]:
    if not (0 <= x <= 100 and 0 <= y <= 100):
        raise ValidationException(f"localizacion_x/y fuera de rango 0-100: ({x}, {y})")
    return float(x), float(y)


def validate_score(value: float, name: str = "score") -> float:
    if not (0 <= value <= 1):
        raise ValidationException(f"{name} debe estar entre 0 y 1: {value}")
    return float(value)


def validate_non_negative(value: float, name: str) -> float:
    if value < 0:
        raise ValidationException(f"{name} no puede ser negativo: {value}")
    return float(value)
