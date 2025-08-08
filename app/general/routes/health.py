from fastapi import APIRouter
from fastapi.responses import JSONResponse

health_router = APIRouter()

@health_router.get("/health/live")
def liveness_probe():
    return JSONResponse(content={"status": "OK"}, status_code=200)

@health_router.get("/health/ready")
def readiness_probe():
    return JSONResponse(content={"status": "OK"}, status_code=200)