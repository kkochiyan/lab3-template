import asyncio
from collections.abc import Awaitable, Callable
from time import monotonic

from app.errors import ServiceUnavailable, UpstreamError


class CircuitBreaker:
    """One circuit per downstream service, shared by reads in a single event loop."""

    def __init__(
        self, service: str, *, failure_threshold: int = 3, recovery_timeout: float = 2,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        self._service = service
        self._threshold = failure_threshold
        self._timeout = recovery_timeout
        self._clock = clock
        self._failures = 0
        self._retry_at: float | None = None
        self._probing = False
        self._generation = 0

    async def call[T](self, operation: Callable[[], Awaitable[T]]) -> T:
        probe = self._retry_at is not None
        if probe:
            if self._probing or self._clock() < self._retry_at:
                raise ServiceUnavailable(self._service)
            # No await between checking and claiming the probe.
            self._probing = True
        generation = self._generation

        try:
            result = await operation()
        except asyncio.CancelledError:
            if probe:
                self._open()
            raise
        except UpstreamError as exc:
            # A 4xx means the service answered; an invalid payload does not.
            if exc.upstream_status is not None and 400 <= exc.upstream_status < 500:
                self._reset_if_current(generation, probe)
            elif generation == self._generation:
                self._failures += 1
                if probe or self._failures >= self._threshold:
                    self._open()
            raise
        except Exception:
            if probe:
                self._open()
            raise
        else:
            self._reset_if_current(generation, probe)
            return result
        finally:
            if probe:
                self._probing = False

    def _open(self) -> None:
        self._retry_at = self._clock() + self._timeout
        self._generation += 1

    def _reset_if_current(self, generation: int, probe: bool) -> None:
        # A request started before opening cannot close the newer circuit.
        if generation == self._generation:
            self._failures = 0
            self._retry_at = None
            if probe:
                self._generation += 1
