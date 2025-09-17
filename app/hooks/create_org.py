from typing import Any


async def create_org(**kwargs: Any) -> dict:
    """Example hook implementation.

    Map an event to this function in .env, e.g.:
    TYK_HOOKS={"pre_create_hook":"create_org"}
    """
    # Return the same kwargs to demonstrate modifiability
    return kwargs
