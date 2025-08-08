from typing import Coroutine, Callable

from .uptime import update_uptime

def get_tasks(
        enable_uptime_background_task: bool = True,
) -> list[Callable[[], Coroutine]]:
    """
    Returns a list of background tasks to be run by the application.
    """
    tasks = []

    if enable_uptime_background_task:
        tasks.append(update_uptime)

    return tasks