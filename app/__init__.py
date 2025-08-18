from fastapi import FastAPI

from .general import general_create_app
from .src import update_app, async_background_tasks

async def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    """

    app, lifespan = general_create_app(
        async_background_tasks=async_background_tasks
    )

    await update_app(app, lifespan)

    return app