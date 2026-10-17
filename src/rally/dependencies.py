"""Inyección de dependencias (repositorios y servicios como singletons)."""

from __future__ import annotations

from functools import lru_cache

from fastapi import Header, Request

from rally.config import Settings
from rally.config import settings as default_settings
from rally.core.security import DeviceFirewall, DeviceIdentity, verify_service_token
from rally.repositories.memory.camera_memory import MemoryCameraRepository
from rally.repositories.memory.detection_memory import MemoryDetectionRepository
from rally.repositories.memory.zone_memory import MemoryZoneRepository
from rally.services.alert_service import AlertService
from rally.services.detection_service import DetectionService
from rally.services.dispatch_service import DispatchService
from rally.services.yolo_client import YoloClient
from rally.services.zone_service import ZoneService


@lru_cache
def get_settings() -> Settings:
    return default_settings


@lru_cache
def get_camera_repo() -> MemoryCameraRepository:
    settings = get_settings()
    return MemoryCameraRepository(settings.camera_registry)


@lru_cache
def get_detection_repo() -> MemoryDetectionRepository:
    settings = get_settings()
    # El archivo que escribe el modelo YOLO (también lo consume la web visual)
    return MemoryDetectionRepository(settings.detections_file)


@lru_cache
def get_zone_repo() -> MemoryZoneRepository:
    return MemoryZoneRepository()


@lru_cache
def get_firewall() -> DeviceFirewall:
    fw = DeviceFirewall(enabled=get_settings().device_firewall)
    fw.load_registry(get_camera_repo().load_raw())
    return fw


@lru_cache
def get_alert_service() -> AlertService:
    return AlertService(get_settings().alert_target_list())


@lru_cache
def get_dispatch_service() -> DispatchService:
    return DispatchService(get_zone_repo(), get_detection_repo())


@lru_cache
def get_yolo_client() -> YoloClient:
    return YoloClient()


def get_detection_service() -> DetectionService:
    return DetectionService(get_detection_repo(), get_zone_repo())


def get_zone_service() -> ZoneService:
    return ZoneService(get_zone_repo(), get_detection_repo())


async def require_registered_device(
    request: Request,
    x_device_id: str | None = Header(default=None),
    x_device_mac: str | None = Header(default=None),
    x_device_ip: str | None = Header(default=None),
) -> DeviceIdentity:
    """Firewall IoT: solo dispositivos dentro del JSON de registro."""
    body_id = None
    if request.method in ("POST", "PUT", "PATCH"):
        try:
            body = await request.json()
            if isinstance(body, dict):
                body_id = body.get("dispositivo_id")
        except Exception:  # noqa: BLE001 - el body puede no ser JSON
            body_id = None
    device_id = x_device_id or body_id
    client_ip = x_device_ip or (request.client.host if request.client else None)
    firewall = get_firewall()
    if not firewall.is_allowed(device_id, x_device_mac, client_ip):
        # Refresca el registro: soporta altas de cámaras posteriores al arranque
        firewall.load_registry(get_camera_repo().load_raw())
    return firewall.require(device_id, x_device_mac, client_ip)


async def require_model_token(x_model_token: str | None = Header(default=None)) -> None:
    """Solo el docker del modelo puede publicar detecciones."""
    verify_service_token(x_model_token, get_settings().model_token)
