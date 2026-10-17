"""Rutas de cámaras / registro de dispositivos IoT."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from rally.core.exceptions import NotFoundError
from rally.core.security import DeviceIdentity
from rally.dependencies import get_camera_repo, require_registered_device
from rally.models.camera import Camera
from rally.repositories.camera_repo import CameraRepository
from rally.schemas.camera import (
    CameraCreate,
    CameraIngestRequest,
    CameraIngestResponse,
    CameraResponse,
)

router = APIRouter(prefix="/api/cameras", tags=["cameras"])


@router.get("", response_model=list[CameraResponse])
def list_cameras(repo: CameraRepository = Depends(get_camera_repo)) -> list[Camera]:
    return repo.list()


@router.get("/{dispositivo_id}", response_model=CameraResponse)
def get_camera(dispositivo_id: str, repo: CameraRepository = Depends(get_camera_repo)) -> Camera:
    cam = repo.get(dispositivo_id)
    if cam is None:
        raise NotFoundError(f"Cámara no registrada: {dispositivo_id}")
    return cam


@router.post("", response_model=CameraResponse, status_code=201)
def register_camera(
    payload: CameraCreate, repo: CameraRepository = Depends(get_camera_repo)
) -> Camera:
    """Alta en el registro: a partir de aquí el firewall deja pasar su push."""
    cam = Camera(**payload.model_dump()).validated()
    return repo.save(cam)


@router.post("/ingest", response_model=CameraIngestResponse)
def camera_push(
    payload: CameraIngestRequest,
    identity: DeviceIdentity = Depends(require_registered_device),
    repo: CameraRepository = Depends(get_camera_repo),
) -> CameraIngestResponse:
    """Push de la cámara IoT (cliente) al servidor. Firewall aplicado.

    El resto de la información del dispositivo se resuelve con la IP/MAC
    leídas del encabezado del push, según el registro de dispositivos.
    """
    cam = repo.get(identity.dispositivo_id)
    if cam is not None and payload.estado:
        cam.estado = payload.estado
        repo.save(cam)
    return CameraIngestResponse(
        status="accepted",
        dispositivo_id=identity.dispositivo_id,
        registrado=True,
        firewall=True,
    )
