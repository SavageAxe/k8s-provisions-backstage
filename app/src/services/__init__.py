import asyncio
import random
from typing import Awaitable, Callable, Tuple, Type, TypeVar, Optional

T = TypeVar("T")


async def retry(
    coro_factory: Callable[[], Awaitable[T]],
    attempts: int = 4,
    base_delay: float = 0.5,
    retry_on: Tuple[Type[BaseException], ...] = (Exception,),
    jitter: float = 0.25,
) -> T:
    """Retry an async operation with exponential backoff and jitter.

    - coro_factory: zero-arg callable returning an awaitable
    - attempts: max attempts (>=1)
    - base_delay: starting delay in seconds
    - retry_on: exception types to retry on
    - jitter: extra random seconds added to each backoff
    """
    last_exc: Optional[BaseException] = None
    for i in range(max(1, attempts)):
        try:
            return await coro_factory()
        except Exception as e:  # noqa: BLE001
            if not isinstance(e, retry_on):
                raise
            last_exc = e
            delay = base_delay * (2 ** i) + random.random() * jitter
            await asyncio.sleep(delay)
    assert last_exc is not None
    raise last_exc
