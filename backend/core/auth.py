"""Minimal opt-in machine-to-machine authentication for external APIs."""

import secrets

from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer

from core.settings import get_settings


_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
_bearer = HTTPBearer(auto_error=False)


async def require_api_key(
    header_key: str = Depends(_api_key_header),
    bearer: HTTPAuthorizationCredentials = Depends(_bearer),
) -> None:
    """Accept either X-API-Key or Authorization: Bearer for /api/v1 routes."""
    settings = get_settings()
    if not settings.api_auth_enabled:
        return

    supplied = header_key
    if not supplied and bearer and bearer.scheme.lower() == "bearer":
        supplied = bearer.credentials

    if not supplied or not secrets.compare_digest(supplied, settings.app_api_key or ""):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error_code": "UNAUTHORIZED",
                "message": "A valid API key is required.",
                "details": None,
            },
            headers={"WWW-Authenticate": "Bearer"},
        )
