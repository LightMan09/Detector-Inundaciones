"""Agrupa todos los routers de la API."""

from __future__ import annotations

from fastapi import APIRouter

from rally.api import alerts, cameras, detections, health, zones

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(cameras.router)
api_router.include_router(detections.router)
api_router.include_router(zones.router)
api_router.include_router(alerts.router)
