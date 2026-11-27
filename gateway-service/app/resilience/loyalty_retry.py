import asyncio
import logging
from collections.abc import Awaitable, Callable
from time import monotonic
from uuid import UUID

from app.errors import ServiceUnavailable, UpstreamError

logger = logging.getLogger(__name__)


class LoyaltyCancellationQueue:
    """Retry idempotent Loyalty cancellations in one background worker."""

    def __init__(
        self, cancel: Callable[[str, UUID], Awaitable[None]], *,
        retry_interval: float = 10, capacity: int = 1000,
    ) -> None:
        self._cancel = cancel
        self._retry_interval = retry_interval
        self._capacity = capacity
        self._pending: set[tuple[str, UUID]] = set()
        self._queue: asyncio.Queue[tuple[float, tuple[str, UUID]]] = asyncio.Queue()

    def enqueue(self, username: str, uid: UUID) -> None:
        job = (username, uid)
        if job in self._pending:
            return
        if len(self._pending) >= self._capacity:
            raise ServiceUnavailable("Loyalty")
        self._pending.add(job)
        self._retry(job)

    def _retry(self, job: tuple[str, UUID]) -> None:
        self._queue.put_nowait((monotonic() + self._retry_interval, job))

    async def run(self) -> None:
        while True:
            ready_at, job = await self._queue.get()
            await asyncio.sleep(max(0, ready_at - monotonic()))
            try:
                await self._cancel(*job)
            except ServiceUnavailable:
                self._retry(job)
            except UpstreamError:
                self._pending.remove(job)
                logger.exception("Loyalty cancellation cannot be retried for %s", job[1])
            else:
                self._pending.remove(job)
