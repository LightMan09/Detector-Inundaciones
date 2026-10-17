"""Helpers geoespaciales puros."""

from __future__ import annotations

import math


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distancia en metros entre dos puntos WGS84."""
    r = 6_371_000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def map_percent_to_pixels(
    x_pct: float, y_pct: float, width: float, height: float
) -> tuple[float, float]:
    """Convierte localizacion_x/localizacion_y (%) a píxeles sobre el mapa."""
    return (x_pct / 100.0 * width, y_pct / 100.0 * height)


def nearest(origin: tuple[float, float], candidates: list[tuple[float, float]]) -> int:
    """Índice del candidato más cercano a origin (coordenadas en % del mapa)."""
    best_idx = -1
    best = float("inf")
    for i, (x, y) in enumerate(candidates):
        d = math.hypot(x - origin[0], y - origin[1])
        if d < best:
            best = d
            best_idx = i
    return best_idx
