"""Cliente HTTP al contenedor del modelo YOLO (Docker 2).

El modelo todavía no está implementado: este cliente solo define el contrato
JSON que usará el docker de visión (context accept: json) para comunicarse con
la API. No se hace inferencia aquí.
"""

from __future__ import annotations

import logging

import httpx

from rally.config import settings
from rally.core.exceptions import ModelUnavailable

logger = logging.getLogger(__name__)


class YoloClient:
    def __init__(self, base_url: str | None = None, token: str | None = None) -> None:
        self.base_url = (base_url or settings.model_api_url).rstrip("/")
        self.token = token if token is not None else settings.model_token

    def _headers(self) -> dict[str, str]:
        return {"X-Model-Token": self.token} if self.token else {}

    def health(self) -> dict:
        """Ping al docker del modelo. Devuelve estado sin lanzar si está caído."""
        try:
            resp = httpx.get(f"{self.base_url}/health", headers=self._headers(), timeout=3.0)
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:  # noqa: BLE001 - el modelo es opcional en el piloto
            logger.info("Modelo YOLO no disponible: %s", exc)
            return {"status": "no_conectado", "detail": str(exc)}

    def request_analysis(self, frame_ref: str, dispositivo_id: str) -> dict:
        """Pide al docker del modelo que analice un frame (pipeline futuro)."""
        try:
            resp = httpx.post(
                f"{self.base_url}/analyze",
                headers=self._headers(),
                json={"frame_ref": frame_ref, "dispositivo_id": dispositivo_id},
                timeout=10.0,
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:  # noqa: BLE001
            raise ModelUnavailable(f"El docker del modelo no respondió: {exc}") from exc
