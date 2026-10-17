"""Middleware HTTP: rate limiting simple por IP (protección del canal de ingestión)."""

from __future__ import annotations

import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_requests_per_minute: int = 120) -> None:
        super().__init__(app)
        self.max = max_requests_per_minute
        self._hits: dict[str, list[float]] = {}

    async def dispatch(self, request: Request, call_next):
        ip = request.client.host if request.client else "unknown"
        now = time.time()
        window = self._hits.setdefault(ip, [])
        window[:] = [t for t in window if now - t < 60]
        if len(window) >= self.max:
            return JSONResponse(
                status_code=429,
                content={"error": "rate_limited", "detail": "Demasiadas solicitudes por minuto"},
            )
        window.append(now)
        return await call_next(request)
