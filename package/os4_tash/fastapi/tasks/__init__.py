"""Background task helpers."""

from typing import Callable, Coroutine

from .uptime import update_uptime


def get_tasks(
    *,
    enable_uptime_background_task: bool = True,
) -> list[Callable[[], Coroutine]]:
    """Return the background tasks requested by the caller."""

    tasks: list[Callable[[], Coroutine]] = []

    if enable_uptime_background_task:
        tasks.append(update_uptime)

    return tasks


__all__ = ["get_tasks", "update_uptime"]
