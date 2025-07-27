from fastapi import FastAPI
from .routers import get_provision_router
from .schemas.loader import SchemaLoader

async_background_tasks = []

def update_app(app: FastAPI) -> FastAPI:
    app.include_router(get_provision_router(SchemaLoader().load_all_schemas()), prefix="/v1")
    return app