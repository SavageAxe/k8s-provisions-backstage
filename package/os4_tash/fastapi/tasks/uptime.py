"""Background task that keeps track of application uptime."""

import asyncio
import time

from prometheus_client import Gauge

UPTIME = Gauge("app_uptime_seconds", "Application uptime in seconds")

_start_time = time.time()


async def update_uptime():  # pragma: no cover - trivial background task
    while True:
        UPTIME.set(time.time() - _start_time)
        await asyncio.sleep(1)


__all__ = ["update_uptime", "UPTIME"]
