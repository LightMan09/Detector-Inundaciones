"""Firewall de dispositivos IoT y autenticación de servicios.

Según el documento de implementación: las cámaras hacen push al servidor y todo
dispositivo que no esté dentro del JSON de registro se bloquea automáticamente
(GET, PUSH, PUT, ...). El registro vive en ``data/seeds/cameras.json``.
"""

from __future__ import annotations

from dataclasses import dataclass

from rally.core.exceptions import DeviceNotAllowed


@dataclass(frozen=True)
class DeviceIdentity:
    dispositivo_id: str
    mac: str
    ip: str


class DeviceFirewall:
    """Permite operar solo a dispositivos presentes en el registro de cámaras."""

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled
        self._allowed: dict[str, DeviceIdentity] = {}

    def load_registry(self, cameras: list[dict]) -> None:
        self._allowed.clear()
        for cam in cameras:
            identity = DeviceIdentity(
                dispositivo_id=str(cam["dispositivo_id"]),
                mac=str(cam.get("mac", "")).upper(),
                ip=str(cam.get("ip", "")),
            )
            self._allowed[identity.dispositivo_id] = identity
            if identity.mac:
                self._allowed[f"mac:{identity.mac}"] = identity
            if identity.ip:
                self._allowed[f"ip:{identity.ip}"] = identity

    def is_allowed(
        self, dispositivo_id: str | None, mac: str | None = None, ip: str | None = None
    ) -> bool:
        if not self.enabled:
            return True
        if dispositivo_id and dispositivo_id in self._allowed:
            return True
        if mac and f"mac:{mac.upper()}" in self._allowed:
            return True
        if ip and f"ip:{ip}" in self._allowed:
            return True
        return False

    def require(
        self, dispositivo_id: str | None, mac: str | None = None, ip: str | None = None
    ) -> DeviceIdentity:
        if not self.is_allowed(dispositivo_id, mac, ip):
            raise DeviceNotAllowed(
                f"Dispositivo no registrado en el firewall "
                f"(id={dispositivo_id!r} mac={mac!r} ip={ip!r})"
            )
        for key in (dispositivo_id, f"mac:{(mac or '').upper()}", f"ip:{ip or ''}"):
            if key and key in self._allowed:
                return self._allowed[key]
        raise DeviceNotAllowed("Dispositivo no registrado")


def verify_service_token(received: str | None, expected: str | None) -> None:
    """Token compartido del docker del modelo o del canal de ingestión."""
    if not expected:
        return
    if not received or received != expected:
        raise DeviceNotAllowed("Token de servicio inválido")
