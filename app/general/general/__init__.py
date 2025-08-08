import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Coroutine, Callable, Any, AsyncGenerator
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from .utils import logger_config, basicSettings
from .database import basic_api
from .routes import add_routers
from .middlewares import add_middlewares
from .tasks import get_tasks

def general_create_app(
    *,
    async_background_tasks: list[Callable[[], Coroutine]] = None,
    enable_logging_middleware: bool = True,
    enable_time_recording_middleware: bool = True,
    enable_root_route: bool = True,
    enable_exception_handlers: bool = True,
    enable_uptime_background_task: bool = True,
    enable_metrics_route: bool = True,
    enable_swagger_routes: bool = True,
    enable_probe_routes: bool = True,
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
        enable_metrics_route: If True, add metrics route.
        enable_swagger_routes: If True, add Swagger UI routes.
        enable_probe_routes: If True, add health check routes.
        **fastapi_kwargs: Additional keyword arguments for FastAPI().
    """

    if async_background_tasks is None:
        async_background_tasks = []

    async_background_tasks.extend(get_tasks(
        enable_uptime_background_task=enable_uptime_background_task,
    ))

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, Any]:
        tasks: list[asyncio.Task] = []

        for coro_fn in async_background_tasks:
            task = asyncio.create_task(coro_fn())
            tasks.append(task)

        try:
            yield  # Startup complete; application runs now
        finally:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

    app = FastAPI(
        **fastapi_kwargs,
        docs_url=None,
        redoc_url=None,
        openapi_url=basicSettings.OPENAPI_JSON_URL,
        lifespan=lifespan,
        root_path=basicSettings.PROXY_LISTEN_PATH,
    )

    static_files_path = Path(__file__).parent.parent / "static"

    @app.get("/static/{full_path:path}")
    async def serve_file(full_path: str):
        file_path = static_files_path / full_path
        if not file_path.exists() or not file_path.is_file():
            raise HTTPException(status_code=404, detail="File not found")
        return FileResponse(file_path)

    app.openapi_version = basicSettings.OPENAPI_VERSION

    add_routers(
        app,
        enable_metrics=enable_metrics_route,
        enable_swagger=enable_swagger_routes,
        enable_probe=enable_probe_routes,
    )

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
            return {"message": f"Welcome to {basicSettings.APP_NAME}!"}

    return app
