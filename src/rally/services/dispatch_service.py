"""Asignación de órdenes y rutas a camiones de presión-succión (ciclo "Actuar").

El camión lleva una cámara con el mismo software: en su ruta detecta más
sumideros tapados, así que la ruta se recalcula con los puntos de mayor riesgo.
"""

from __future__ import annotations

import uuid

from rally.models.zone import CriticalPoint
from rally.repositories.zone_repo import ZoneRepository
from rally.schemas.zone import DispatchOrder, DispatchResponse
from rally.utils.geo import nearest


class DispatchService:
    def __init__(
        self,
        zones: ZoneRepository,
        detections=None,
        camiones: list[dict] | None = None,
    ) -> None:
        self.zones = zones
        self.detections = detections
        # Flota actual EAAB (sin comprar hardware nuevo): posición sobre el mapa %
        self.camiones = camiones or [
            {"camion_id": "EAAB-PR-01", "localizacion_x": 30, "localizacion_y": 35},
            {"camion_id": "EAAB-PR-02", "localizacion_x": 55, "localizacion_y": 45},
            {"camion_id": "EAAB-PR-03", "localizacion_x": 70, "localizacion_y": 60},
        ]

    def generate_orders(self, max_points: int = 6) -> DispatchResponse:
        """Greedy: cada camión toma el punto crítico más cercano por prioridad."""
        if self.detections is not None:
            self.zones.derive_from(self.detections.list())
        pending = sorted(
            self.zones.list_points(), key=lambda p: p.riesgo, reverse=True
        )[:max_points]
        camiones = [dict(c) for c in self.camiones]
        ordenes: list[DispatchOrder] = []
        for priority, point in enumerate(pending, start=1):
            if not camiones:
                break
            idx = nearest(
                (point.localizacion_x, point.localizacion_y),
                [(c["localizacion_x"], c["localizacion_y"]) for c in camiones],
            )
            truck = camiones.pop(idx)
            route = self._build_route(truck, point)
            ordenes.append(
                DispatchOrder(
                    orden_id=f"OT-{uuid.uuid4().hex[:6].upper()}",
                    camion_id=truck["camion_id"],
                    punto_critico_id=point.punto_id,
                    prioridad=priority,
                    ruta=route,
                    accion="presion-succion",
                    estado="asignada",
                    distancia_estimada_km=self._distance_km(truck, point),
                )
            )
        return DispatchResponse(generadas=len(ordenes), ordenes=ordenes)

    def _build_route(self, truck: dict, point: CriticalPoint) -> list[str]:
        route = [f"Salida {truck['camion_id']}"]
        route.append(f"{point.nombre} ({point.barrio})")
        if point.cobertura_basura_pct > 40:
            route.append("Recolección de residuos a recicladores de oficio")
        route.append("Retorno EAAB")
        return route

    @staticmethod
    def _distance_km(truck: dict, point: CriticalPoint) -> float:
        # Escala aproximada: 1% del mapa de Engativá ~ 0.18 km
        dx = point.localizacion_x - truck["localizacion_x"]
        dy = point.localizacion_y - truck["localizacion_y"]
        return round(((dx**2 + dy**2) ** 0.5) * 0.18, 2)
