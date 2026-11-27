import asyncio
from unittest import IsolatedAsyncioTestCase

from app.errors import ServiceUnavailable, UpstreamError
from app.resilience.circuit_breaker import CircuitBreaker


class CircuitBreakerTest(IsolatedAsyncioTestCase):
    async def test_open_rejects_traffic_and_only_one_probe_can_close(self):
        now = 0
        circuit = CircuitBreaker("Loyalty", failure_threshold=2, clock=lambda: now)
        calls = 0
        started = asyncio.Event()
        ready = asyncio.Event()

        async def unavailable():
            nonlocal calls
            calls += 1
            raise ServiceUnavailable("Loyalty")

        async def probe():
            started.set()
            await ready.wait()
            return "recovered"

        for _ in range(3):
            with self.assertRaises(ServiceUnavailable):
                await circuit.call(unavailable)
        self.assertEqual(calls, 2)

        now = 2
        with self.assertRaises(ServiceUnavailable):
            await circuit.call(unavailable)
        with self.assertRaises(ServiceUnavailable):
            await circuit.call(unavailable)
        self.assertEqual(calls, 3)

        now = 4
        task = asyncio.create_task(circuit.call(probe))
        try:
            await started.wait()
            with self.assertRaises(ServiceUnavailable):
                await circuit.call(unavailable)
        finally:
            ready.set()
            self.assertEqual(await task, "recovered")
        with self.assertRaises(ServiceUnavailable):
            await circuit.call(unavailable)
        self.assertEqual(calls, 4)

    async def test_business_errors_do_not_open_circuit(self):
        circuit = CircuitBreaker("Reservation", failure_threshold=1)

        async def missing():
            raise UpstreamError("Reservation", upstream_status=404)

        for _ in range(2):
            with self.assertRaises(UpstreamError) as error:
                await circuit.call(missing)
            self.assertEqual(error.exception.upstream_status, 404)

    async def test_stale_success_cannot_close_open_circuit(self):
        circuit = CircuitBreaker("Payment", failure_threshold=1)
        started = asyncio.Event()
        ready = asyncio.Event()

        async def slow_success():
            started.set()
            await ready.wait()

        async def unavailable():
            raise ServiceUnavailable("Payment")

        task = asyncio.create_task(circuit.call(slow_success))
        try:
            await started.wait()
            with self.assertRaises(ServiceUnavailable):
                await circuit.call(unavailable)
        finally:
            ready.set()
            await task

        async def unexpected():
            self.fail("Open circuit let a request through")

        with self.assertRaises(ServiceUnavailable):
            await circuit.call(unexpected)
