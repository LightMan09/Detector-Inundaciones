"""Alertas a EAAB / IDIGER / Movilidad / operador de aseo (ciclo "Actuar")."""

from __future__ import annotations

import logging
import uuid

from rally.core.constants import ALERT_TARGETS
from rally.schemas.zone import AlertCreate, AlertResponse
from rally.utils.datetime_utils import iso, utcnow

logger = logging.getLogger(__name__)


class AlertService:
    """Genera la alerta y "notifica" a las entidades (log + payload de demo)."""

    def __init__(self, targets: list[str] | None = None) -> None:
        self.targets = targets or list(ALERT_TARGETS)
        self._alerts: list[AlertResponse] = []

    def create(self, payload: AlertCreate, targets: list[str] | None = None) -> AlertResponse:
        notificados = targets or self.targets
        alert = AlertResponse(
            alerta_id=f"ALERT-{uuid.uuid4().hex[:8].upper()}",
            titulo=payload.titulo,
            severidad=payload.severidad,
            upz=payload.upz,
            punto_critico_id=payload.punto_critico_id,
            detalle=payload.detalle,
            timestamp=iso(utcnow()),
            notificados=notificados,
        )
        self._alerts.insert(0, alert)
        logger.warning(
            "ALERTA %s [%s] %s -> %s",
            alert.alerta_id,
            alert.severidad,
            alert.titulo,
            ",".join(notificados),
        )
        return alert

    def list(self) -> list[AlertResponse]:
        return list(self._alerts)
