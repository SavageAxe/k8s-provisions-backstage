from fastapi import APIRouter
from fastapi.responses import JSONResponse
from ..utils import basicSettings

health_router = APIRouter()

@health_router.get(basicSettings.PROBE_LIVENESS_PATH)
def liveness_probe():
    return JSONResponse(content={"status": "OK"}, status_code=200)

@health_router.get(basicSettings.PROBE_READINESS_PATH)
def readiness_probe():
    return JSONResponse(content={"status": "OK"}, status_code=200)