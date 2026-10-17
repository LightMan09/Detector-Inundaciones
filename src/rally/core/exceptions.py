"""Excepciones propias de SAPO."""

from fastapi import Request, status
from fastapi.responses import JSONResponse


class SapoException(Exception):
    """Error base del dominio."""

    status_code = status.HTTP_400_BAD_REQUEST
    code = "sapo_error"

    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


class DeviceNotAllowed(SapoException):
    """El dispositivo IoT no está en el registro (firewall)."""

    status_code = status.HTTP_403_FORBIDDEN
    code = "device_not_allowed"


class NotFoundError(SapoException):
    status_code = status.HTTP_404_NOT_FOUND
    code = "not_found"


class ValidationException(SapoException):
    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    code = "validation_error"


class ModelUnavailable(SapoException):
    """El contenedor del modelo YOLO no respondió."""

    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    code = "model_unavailable"


def sapo_exception_handler(_request: Request, exc: SapoException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.code, "detail": exc.detail},
    )
