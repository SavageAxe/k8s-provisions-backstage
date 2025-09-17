"""Reusable FastAPI application factory."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncGenerator, Callable, Coroutine

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from .middlewares import add_middlewares
from .routes import add_routers
from .tasks import get_tasks
from .utils import basicSettings


def general_create_app(
    *,
    async_background_tasks: list[Callable[[], Coroutine]] | None = None,
    enable_logging_middleware: bool = True,
    enable_time_recording_middleware: bool = True,
    enable_root_route: bool = True,
    enable_exception_handlers: bool = True,
    enable_uptime_background_task: bool = True,
    enable_metrics_route: bool = True,
    enable_swagger_routes: bool = True,
    enable_probe_routes: bool = True,
    **fastapi_kwargs: Any,
) -> FastAPI:
    """Create and configure a FastAPI application.

    The helper mirrors the behaviour of the in-repo application factory so
    services can share the same bootstrapping logic.
    """

    if async_background_tasks is None:
        async_background_tasks = []

    async_background_tasks.extend(
        get_tasks(enable_uptime_background_task=enable_uptime_background_task)
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, Any]:
        tasks: list[asyncio.Task] = []

        for coro_fn in async_background_tasks:
            task = asyncio.create_task(coro_fn())
            tasks.append(task)

        try:
            yield
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

    static_files_path = Path(__file__).resolve().parent.parent / "static"

    @app.get("/static/{full_path:path}")
    async def serve_file(full_path: str):  # pragma: no cover - simple file response
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
    async def get_openapi():  # pragma: no cover - simple response handler
        return app.openapi()

    if enable_root_route:
        @app.get("/", response_model=dict, status_code=200)
        def read_root():  # pragma: no cover - simple response handler
            return {"message": f"Welcome to {basicSettings.APP_NAME}!"}

    return app


# ``general_create_app`` is the primary entrypoint but ``create_app`` mirrors the
# naming convention of the service package for convenience.
create_app = general_create_app

__all__ = ["general_create_app", "create_app"]
