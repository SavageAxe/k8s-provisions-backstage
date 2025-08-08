from fastapi import APIRouter, Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

metrics_router = APIRouter(prefix="/metrics")

@metrics_router.get("/")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
