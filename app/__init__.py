from fastapi import FastAPI

from .general import general_create_app
from .src import update_app, async_background_tasks

def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    """

    app = general_create_app(
        async_background_tasks=async_background_tasks
    )

    update_app(app)

    return app