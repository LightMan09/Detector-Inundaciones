"""Implementación en memoria del repositorio de zonas.

Las zonas y puntos críticos ya no vienen de un JSON precargado: se derivan de
las detecciones del modelo (cada evento trae ``localizacion_x/y`` y su UPZ).
"""

from __future__ import annotations

from rally.models.detection import Detection
from rally.models.zone import CriticalPoint, Zone
from rally.repositories.zone_repo import ZoneRepository

SEVERIDAD_A_ALERTA = {"critico": "roja", "alto": "naranja", "medio": "amarilla", "leve": "verde"}


class MemoryZoneRepository(ZoneRepository):
    def __init__(self) -> None:
        self._zones: dict[str, Zone] = {}
        self._points: dict[str, CriticalPoint] = {}

    def derive_from(self, detections: list[Detection]) -> None:
        """Reconstruye UPZ y puntos críticos a partir del JSON del modelo."""
        puntos: dict[str, CriticalPoint] = {}
        por_upz: dict[str, list[CriticalPoint]] = {}
        for det in detections:
            if det.clase == "limpia":
                continue  # la limpieza confirmada no es un punto crítico
            point = CriticalPoint(
                punto_id=det.evento_id,
                nombre=f"{det.barrio or 'Engativá'} ({det.clase_modelo or det.clase})",
                upz=det.upz or "UPZ sin asignar",
                barrio=det.barrio,
                localizacion_x=det.localizacion_x,
                localizacion_y=det.localizacion_y,
                nivel_agua_cm=det.nivel_agua_cm,
                cobertura_basura_pct=det.cobertura_basura_pct,
                riesgo=0.0,
                severidad=det.severity,
                tipo_afectacion="drenaje lento" if det.drena_lento else "encharcamiento",
                repeticion_30d=1,
                lluvia_prevista_mm=det.lluvia_mm_h,
                barrios_afectados=[det.barrio] if det.barrio else [],
            )
            puntos[point.punto_id] = point
            por_upz.setdefault(point.upz, []).append(point)

        self._points = puntos
        self._zones = {}
        for upz, pts in por_upz.items():
            worst = max(pts, key=lambda p: p.nivel_agua_cm + p.cobertura_basura_pct / 2)
            orden = ("leve", "medio", "alto", "critico")
            riesgo = max((p.severidad for p in pts), key=lambda s: orden.index(s))
            codigo = upz.replace("UPZ", "").strip().split(" ")[0] if upz.startswith("UPZ") else ""
            self._zones[upz] = Zone(
                zona_id=upz.lower().replace(" ", "_"),
                codigo=codigo,
                nombre=upz,
                riesgo=0.0,
                severidad=riesgo,
                estado_alerta=SEVERIDAD_A_ALERTA.get(riesgo, "verde"),
                puntos=pts,
                barrios=sorted({p.barrio for p in pts if p.barrio}),
                resumen=worst.nombre,
            )

    def list(self) -> list[Zone]:
        return sorted(self._zones.values(), key=lambda z: z.riesgo, reverse=True)

    def get(self, key: str) -> Zone | None:
        return self._zones.get(key)

    def save(self, item: Zone) -> Zone:
        self._zones[item.zona_id] = item
        return item

    def delete(self, key: str) -> bool:
        return self._zones.pop(key, None) is not None

    def list_points(self) -> list[CriticalPoint]:
        return sorted(self._points.values(), key=lambda p: p.riesgo, reverse=True)

    def get_point(self, punto_id: str) -> CriticalPoint | None:
        return self._points.get(punto_id)

    def save_point(self, point: CriticalPoint) -> CriticalPoint:
        self._points[point.punto_id] = point
        for zone in self._zones.values():
            if point.upz and point.upz == zone.nombre:
                zone.puntos = [point if p.punto_id == point.punto_id else p for p in zone.puntos]
        return point
