"""Health check del servicio."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from rally import __version__
from rally.config import Settings
from rally.dependencies import get_camera_repo, get_settings, get_yolo_client
from rally.repositories.camera_repo import CameraRepository
from rally.schemas.common import HealthResponse
from rally.services.yolo_client import YoloClient

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health(
    settings: Settings = Depends(get_settings),
    cameras: CameraRepository = Depends(get_camera_repo),
    yolo: YoloClient = Depends(get_yolo_client),
) -> HealthResponse:
    model = yolo.health()
    return HealthResponse(
        status="ok",
        app=settings.app_name,
        version=__version__,
        devices_registered=len(cameras.list()),
        yolo_model=model.get("status", "no_conectado"),
    )
