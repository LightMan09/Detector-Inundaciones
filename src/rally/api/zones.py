"""Rutas de zonas y puntos críticos (UPZ Engativá)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from rally.core.constants import UPZ_ENGATIVA
from rally.core.exceptions import NotFoundError
from rally.dependencies import get_zone_service
from rally.models.zone import CriticalPoint, Zone
from rally.schemas.zone import CriticalPointResponse, ZoneRankingResponse, ZoneResponse
from rally.services.zone_service import ZoneService

router = APIRouter(prefix="/api/zones", tags=["zones"])


@router.get("", response_model=ZoneRankingResponse)
def list_zones(service: ZoneService = Depends(get_zone_service)) -> ZoneRankingResponse:
    items = service.ranking()
    return ZoneRankingResponse(total=len(items), items=items)


@router.get("/upz")
def list_upz() -> list[dict]:
    """Catálogo de las 9 UPZ del piloto (Localidad 10)."""
    return UPZ_ENGATIVA


@router.get("/critical", response_model=list[CriticalPointResponse])
def critical_points(
    min_risk: float = Query(default=0, ge=0, le=100),
    service: ZoneService = Depends(get_zone_service),
) -> list[CriticalPoint]:
    return service.critical_points(min_risk)


@router.get("/{zona_id}", response_model=ZoneResponse)
def get_zone(zona_id: str, service: ZoneService = Depends(get_zone_service)) -> Zone:
    zone = service.zones.get(zona_id)
    if zone is None:
        raise NotFoundError(f"Zona no encontrada: {zona_id}")
    return zone
