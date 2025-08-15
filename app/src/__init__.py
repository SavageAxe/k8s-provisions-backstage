from fastapi import FastAPI
from .routers import generate_router
from .middlewares.exception import add_exception_handlers

async_background_tasks = []

def update_app(app: FastAPI) -> FastAPI:
    add_exception_handlers(app)
    app = generate_router(app)
    return app