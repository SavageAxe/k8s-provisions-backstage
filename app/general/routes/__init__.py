from .swagger import router as swagger_router
from .metrics import metrics_router

routers = [swagger_router, metrics_router]

def add_routers(app):
    """
    Add all routers to the FastAPI application.
    """
    for router in routers:
        app.include_router(router, include_in_schema=False)