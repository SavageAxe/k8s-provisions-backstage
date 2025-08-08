from .swagger import router as swagger_router
from .metrics import metrics_router
from .probes import health_router

def add_routers(
        app,
        enable_swagger: bool = True,
        enable_metrics: bool = True,
        enable_probe: bool = True,
):
    """
    Add all routers to the FastAPI application.
    """

    if enable_swagger:
        app.include_router(swagger_router, include_in_schema=False)

    if enable_metrics:
        app.include_router(metrics_router, include_in_schema=False)

    if enable_probe:
        app.include_router(health_router, include_in_schema=False)