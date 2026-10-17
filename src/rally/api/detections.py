"""Rutas de detecciones: entrada JSON del docker del modelo (Docker 2)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from rally.dependencies import (
    get_alert_service,
    get_detection_repo,
    get_detection_service,
    require_model_token,
)
from rally.repositories.detection_repo import DetectionRepository
from rally.schemas.detection import DetectionAck, DetectionCreate, DetectionListResponse
from rally.schemas.zone import AlertCreate
from rally.services.alert_service import AlertService
from rally.services.detection_service import DetectionService

router = APIRouter(prefix="/api/detections", tags=["detections"])


@router.get("", response_model=DetectionListResponse)
def list_detections(
    limit: int = Query(default=50, ge=1, le=500),
    repo: DetectionRepository = Depends(get_detection_repo),
) -> DetectionListResponse:
    todos = repo.list()
    return DetectionListResponse(total=len(todos), items=todos[:limit])


@router.post("", response_model=DetectionAck, dependencies=[Depends(require_model_token)])
def receive_detections(
    payload: DetectionCreate,
    service: DetectionService = Depends(get_detection_service),
    alerts: AlertService = Depends(get_alert_service),
) -> DetectionAck:
    """Context accept: json — único canal por el que entran detecciones."""
    result = service.ingest(payload.detections)
    generated = 0
    for det in payload.detections:
        if det.severity in ("critico", "alto"):
            alerts.create(
                AlertCreate(
                    titulo=f"Encharcamiento {det.severity}: {det.barrio or det.punto_critico_id}",
                    severidad=det.severity,
                    upz=det.upz,
                    punto_critico_id=det.punto_critico_id,
                    detalle=f"nivel={det.nivel_agua_cm}cm basura={det.cobertura_basura_pct}%",
                )
            )
            generated += 1
    return DetectionAck(
        recibidas=result["recibidas"],
        criticas=result["criticas"],
        alertas_generadas=generated,
    )


@router.get("/summary")
def detections_summary(service: DetectionService = Depends(get_detection_service)) -> dict:
    return service.summary()
