"""Prometheus metrics endpoint."""

from fastapi import APIRouter, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

metrics_router = APIRouter(prefix="/metrics")


@metrics_router.get("/")
def metrics() -> Response:
    """Expose the collected Prometheus metrics."""

    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


__all__ = ["metrics_router", "metrics"]
