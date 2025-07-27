import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Coroutine
from fastapi import FastAPI
from starlette.staticfiles import StaticFiles

from .utils import logger_config, basicSettings
from .database import basic_api
from .routes import add_routers
from .middlewares import add_middlewares
from .tasks import get_tasks

def general_create_app(
    *,
    async_background_tasks: list[Coroutine] = None,
    enable_logging_middleware: bool = True,
    enable_time_recording_middleware: bool = True,
    enable_root_route: bool = True,
    enable_exception_handlers: bool = True,
    enable_uptime_background_task: bool = True,
    **fastapi_kwargs
) -> FastAPI:
    """
    Create and configure the FastAPI application.

    Args:
        async_background_tasks: A list of background tasks to execute.
        enable_logging_middleware: If True, add basic logging middleware.
        enable_time_recording_middleware: If True, add request time recording middleware.
        enable_root_route: If True, add the root '/' route.
        enable_exception_handlers: If True, add exception handlers.
        enable_uptime_background_task: If true, add uptime background task.
        **fastapi_kwargs: Additional keyword arguments for FastAPI().
    """

    if async_background_tasks is None:
        async_background_tasks = []

    async_background_tasks.extend(get_tasks(
        enable_uptime_background_task=enable_uptime_background_task,
    ))

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        for task in async_background_tasks:
            asyncio.create_task(task)
        yield

    app = FastAPI(
        **fastapi_kwargs,
        docs_url=None,
        redoc_url=None,
        openapi_url=basicSettings.SWAGGER_OPENAPI_JSON_URL,
        lifespan=lifespan,
    )

    static_files_path = Path(__file__).parent.parent / "static"
    app.mount("/static", StaticFiles(directory=static_files_path), name="static")

    add_routers(app)

    add_middlewares(
        app,
        enable_request_logging=enable_logging_middleware,
        enable_request_timing=enable_time_recording_middleware,
        enable_exception_handlers=enable_exception_handlers,
    )

    @app.get(basicSettings.SWAGGER_OPENAPI_JSON_URL, include_in_schema=False)
    async def get_openapi():
        """
        Endpoint to serve the OpenAPI schema.
        """
        return app.openapi()

    if enable_root_route:
        @app.get("/", response_model=dict, status_code=200)
        def read_root():
            """
            Root endpoint that returns a simple message.
            """
            return {"message": f"Welcome to the {basicSettings.APP_NAME}!"}

    return app
