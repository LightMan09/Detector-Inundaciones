"""Fixtures compartidas de tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from rally.config import settings as app_settings
from rally.dependencies import (
    get_alert_service,
    get_camera_repo,
    get_detection_repo,
    get_dispatch_service,
    get_firewall,
    get_settings,
    get_yolo_client,
    get_zone_repo,
)
from rally.main import create_app


def _reset_caches() -> None:
    for fn in (
        get_settings,
        get_camera_repo,
        get_detection_repo,
        get_zone_repo,
        get_firewall,
        get_alert_service,
        get_dispatch_service,
        get_yolo_client,
    ):
        fn.cache_clear()


@pytest.fixture()
def client(tmp_path):
    _reset_caches()
    app_settings.model_token = "test-token"
    # Aislamiento: los tests no tocan data/live del repo
    app_settings.camera_registry = tmp_path / "camaras.json"
    app_settings.detections_file = tmp_path / "detecciones.json"
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client
    _reset_caches()
    app_settings.model_token = ""
    app_settings.camera_registry = Path("data/live/camaras.json")
    app_settings.detections_file = Path("data/live/detecciones.json")


@pytest.fixture()
def model_headers() -> dict[str, str]:
    return {"X-Model-Token": "test-token"}


@pytest.fixture()
def evento_base() -> dict:
    return {
        "evento_id": "YOLO-TEST-000001",
        "dispositivo_id": "camara_modelo_01",
        "origen": "yolo_docker",
        "clase": "agua",
        "clase_modelo": "con_agua",
        "estado": "INUNDADA",
        "confianza": 0.91,
        "nivel_agua_cm": 44.0,
        "cobertura_basura_pct": 0.0,
        "drena_lento": False,
        "tiempo_drenaje_s": None,
        "localizacion_x": 27.5,
        "localizacion_y": 38.2,
        "upz": "UPZ 31 Santa Cecilia",
        "barrio": "Quirigua",
    }
