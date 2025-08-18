from fastapi import FastAPI
from .routers import generate_router
from .middlewares.exception import add_exception_handlers
from contextlib import asynccontextmanager
import asyncio

async_background_tasks = []

def extend_lifespan(original_lifespan):
    @asynccontextmanager
    async def wrapper(app):
        # startup: add schema sync
        tasks = []
        for rg in getattr(app.state, "router_generators", []):
            tasks.append(asyncio.create_task(rg.schema_manager.sync_schemas()))

        # run the original lifespan
        async with original_lifespan(app):
            yield

        # shutdown: cancel schema sync
        for t in tasks:
            t.cancel()
            try:
                await t
            except asyncio.CancelledError:
                pass

    return wrapper

async def update_app(app: FastAPI, current_lifespan) -> FastAPI:
    add_exception_handlers(app)
    app.state.router_generators = []
    app = await generate_router(app)
    app.router.lifespan_context = extend_lifespan(current_lifespan)
    return app