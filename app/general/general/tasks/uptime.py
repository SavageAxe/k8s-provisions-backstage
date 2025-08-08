import time
import asyncio
from prometheus_client import Gauge

UPTIME = Gauge("app_uptime_seconds", "Application uptime in seconds")

start_time = time.time()

# Async background task to update uptime
async def update_uptime():
    while True:
        UPTIME.set(time.time() - start_time)
        await asyncio.sleep(1)