"""Alertas a entidades y despacho de camiones de presión-succión (ciclo "Actuar")."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from rally.dependencies import get_alert_service, get_dispatch_service
from rally.schemas.zone import AlertCreate, AlertResponse, DispatchResponse
from rally.services.alert_service import AlertService
from rally.services.dispatch_service import DispatchService

router = APIRouter(prefix="/api", tags=["alerts"])


@router.get("/alerts", response_model=list[AlertResponse])
def list_alerts(alerts: AlertService = Depends(get_alert_service)) -> list[AlertResponse]:
    return alerts.list()


@router.post("/alerts", response_model=AlertResponse, status_code=201)
def create_alert(
    payload: AlertCreate,
    alerts: AlertService = Depends(get_alert_service),
) -> AlertResponse:
    """Alerta manual (COE Engativá) o generada por priorización automática."""
    return alerts.create(payload)


@router.post("/dispatch", response_model=DispatchResponse)
def dispatch_orders(dispatch: DispatchService = Depends(get_dispatch_service)) -> DispatchResponse:
    """Asigna orden y ruta a los camiones EAAB por prioridad de riesgo."""
    return dispatch.generate_orders()
