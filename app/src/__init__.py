from fastapi import FastAPI
from .routers import get_provision_router
from .schemas.loader import SchemaLoader
from .middlewares.exception import add_exception_handlers

async_background_tasks = []


def update_app(app: FastAPI) -> FastAPI:
    add_exception_handlers(app)
    app.include_router(get_provision_router(app), prefix="/v1")
    return app