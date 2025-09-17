"""Liveness and readiness probe endpoints."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from ..utils import basicSettings

health_router = APIRouter()


@health_router.get(basicSettings.PROBE_LIVENESS_PATH)
def liveness_probe() -> JSONResponse:
    """Return a success payload for Kubernetes liveness probes."""

    return JSONResponse(content={"status": "OK"}, status_code=200)


@health_router.get(basicSettings.PROBE_READINESS_PATH)
def readiness_probe() -> JSONResponse:
    """Return a success payload for Kubernetes readiness probes."""

    return JSONResponse(content={"status": "OK"}, status_code=200)


__all__ = ["health_router", "liveness_probe", "readiness_probe"]
