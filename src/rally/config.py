"""Settings de la aplicación (pydantic-settings)."""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SAPO_", env_file=".env", extra="ignore")

    app_name: str = "SAPO API"
    debug: bool = False
    data_dir: Path = Path("data")

    # JSON que produce el modelo (Docker YOLO) y que consume la web visual
    detections_file: Path = Path("data/live/detecciones.json")
    # Registro de dispositivos (firewall IoT), se llena en runtime con POST /api/cameras
    camera_registry: Path = Path("data/live/camaras.json")
    device_firewall: bool = True

    # Docker 2: contrato con el contenedor YOLO (aún no implementado)
    model_api_url: str = "http://yolo:8001"
    model_token: str = ""
    ingest_token: str = ""

    max_cameras: int = 200
    max_requests_per_minute: int = 120
    detection_ttl_hours: int = 48

    alert_targets: str = "EAAB,IDIGER,MOVILIDAD,ASEO"

    @property
    def live_dir(self) -> Path:
        return self.data_dir / "live"

    @property
    def maps_dir(self) -> Path:
        return self.data_dir / "maps"

    def alert_target_list(self) -> list[str]:
        return [t.strip().upper() for t in self.alert_targets.split(",") if t.strip()]


settings = Settings()
