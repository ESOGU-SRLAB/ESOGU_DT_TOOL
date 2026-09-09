"""Container liveness and dependency readiness endpoints."""

import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict, Optional
from pymongo import MongoClient

from core.settings import get_settings


router = APIRouter(tags=["operations"])


class HealthResponse(BaseModel):
    status: str
    service: str
    timestamp: str


class ReadinessResponse(BaseModel):
    status: str
    dependencies: Dict[str, str]
    error_code: Optional[str] = None
    message: Optional[str] = None
    details: Optional[Dict[str, str]] = None
    job_id: Optional[str] = None


def check_database_ready() -> None:
    settings = get_settings()
    client = MongoClient(settings.mongo_uri, serverSelectionTimeoutMS=2000)
    try:
        client.admin.command("ping")
    finally:
        client.close()


@router.get("/health", summary="Process liveness", response_model=HealthResponse)
async def health():
    return {
        "status": "ok",
        "service": "stlc-manager-backend",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/ready", summary="Critical dependency readiness", response_model=ReadinessResponse)
async def ready():
    try:
        await asyncio.to_thread(check_database_ready)
    except Exception:
        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready",
                "dependencies": {"database": "unavailable"},
                "error_code": "DATABASE_UNAVAILABLE",
                "message": "The required database is unavailable.",
                "details": {"database": "unavailable"},
                "job_id": None,
            },
        )
    return {"status": "ready", "dependencies": {"database": "available"}}
