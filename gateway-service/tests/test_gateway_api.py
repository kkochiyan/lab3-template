import asyncio
import json
from unittest import IsolatedAsyncioTestCase
from unittest.mock import patch
from uuid import uuid4

import httpx

from app.clients.loyalty import LoyaltyClient
from app.clients.payments import PaymentClient
from app.clients.reservations import ReservationClient
from app.main import app
from app.resilience.loyalty_retry import LoyaltyCancellationQueue
from app.services.bookings import BookingService


class GatewayApiTest(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.hotel_uid, self.reservation_uid, self.payment_uid = (str(uuid4()) for _ in range(3))
        self.headers = {"X-User-Name": "Test Max"}
        self.data = {"hotelUid": self.hotel_uid, "startDate": "2021-10-08", "endDate": "2021-10-11"}
        self.loyalty = {"status": "GOLD", "discount": 10, "reservationCount": 25}
        self.payment = {"paymentUid": self.payment_uid, "status": "PAID", "price": 27000}
        self.record = {
            "reservationUid": self.reservation_uid,
            "paymentUid": self.payment_uid,
            "startDate": self.data["startDate"],
            "endDate": self.data["endDate"],
            "hotel": {"hotelUid": self.hotel_uid, "name": "Hotel", "fullAddress": "Москва", "stars": 5},
            "status": "PAID",
        }
        self.hotel = {
            "hotelUid": self.hotel_uid, "name": "Hotel", "country": "Россия",
            "city": "Москва", "address": "Улица 1", "stars": 5, "price": 10000,
        }
        self.calls = []
        self.failures = {}
        transport = httpx.MockTransport(self.upstream)
        clients = []
        for host in ("reservation", "payment", "loyalty"):
            client = httpx.AsyncClient(transport=transport, base_url=f"http://{host}")
            clients.append(client)
            self.addAsyncCleanup(client.aclose)
        reservation = ReservationClient(clients[0])
        loyalty = LoyaltyClient(clients[2])
        self.retries = LoyaltyCancellationQueue(loyalty.cancel_reservation, retry_interval=0.01)
        state = patch.dict(
            app.state._state,
            {
                "reservation_client": reservation,
                "booking_service": BookingService(
                    reservation, PaymentClient(clients[1]), loyalty, self.retries,
                ),
            },
        )
        state.start()
        self.addCleanup(state.stop)
        self.client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://gateway"
        )
        self.addAsyncCleanup(self.client.aclose)

    def upstream(self, request):
        host = request.url.host
        method = request.method
        path = request.url.path
        self.calls.append((host, method, path))
        failure = self.failures.get((host, method, path))
        if failure == "disconnected":
            raise httpx.ConnectError("offline", request=request)
        if failure == "timeout":
            raise httpx.ReadTimeout("upstream timeout", request=request)
        if failure == "malformed":
            return httpx.Response(200, json={"unexpected": True})
        if failure is not None:
            return httpx.Response(failure)
        if host in ("reservation", "loyalty") and "/hotels" not in path:
            self.assertEqual(request.headers["X-User-Name"], "Test Max")
        if path.endswith(f"/hotels/{self.hotel_uid}"):
            return httpx.Response(200, json=self.hotel)
        if method == "GET" and path.endswith("/loyalty"):
            return httpx.Response(200, json=self.loyalty)
        if method == "POST" and host == "payment":
            self.assertEqual(json.loads(request.content), {"price": 27000})
            return httpx.Response(201, json=self.payment)
        if method == "POST" and host == "reservation":
            self.assertEqual(json.loads(request.content), self.data | {"paymentUid": self.payment_uid})
            return httpx.Response(201, json=self.record)
        if method == "GET" and path.endswith("/reservations"):
            return httpx.Response(200, json=[self.record])
        if method == "GET" and path.endswith(f"/reservations/{self.reservation_uid}"):
            return httpx.Response(200, json=self.record)
        if method == "GET" and path.endswith(f"/payments/{self.payment_uid}"):
            return httpx.Response(200, json=self.payment)
        if host == "loyalty" and method in ("PUT", "DELETE"):
            return httpx.Response(200, json=self.loyalty)
        if method == "DELETE" and host in ("reservation", "payment"):
            return httpx.Response(204)
        raise AssertionError(f"Unexpected upstream request: {request}")

    async def test_create_uses_discount_before_registering_and_omits_internal_uid(self):
        response = await self.client.post("/api/v1/reservations", json=self.data, headers=self.headers)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json(), self.data | {
            "reservationUid": self.reservation_uid, "discount": 10,
            "status": "PAID", "payment": {"status": "PAID", "price": 27000},
        })
        self.assertEqual([(host, method) for host, method, _ in self.calls], [
            ("reservation", "GET"), ("loyalty", "GET"), ("payment", "POST"),
            ("reservation", "POST"), ("loyalty", "PUT"),
        ])

    async def test_invalid_booking_never_calls_upstream(self):
        response = await self.client.post(
            "/api/v1/reservations", json=self.data | {"endDate": "2021-10-07"},
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["errors"][0]["field"], "endDate")
        self.assertEqual(self.calls, [])

    async def test_me_joins_with_payment_and_loyalty(self):
        response = await self.client.get("/api/v1/me", headers=self.headers)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["loyalty"], self.loyalty)
        reservation = response.json()["reservations"][0]
        self.assertNotIn("paymentUid", reservation)
        self.assertEqual(reservation["payment"]["price"], 27000)

    async def test_known_and_ambiguous_reservation_failures(self):
        route = "/api/v1/reservations"
        upstream = ("reservation", "POST", "/internal/v1/reservations")
        self.failures[upstream] = 404
        response = await self.client.post(route, json=self.data, headers=self.headers)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["errors"][0]["field"], "hotelUid")
        self.assertEqual(self.calls[-1], ("payment", "DELETE", f"/internal/v1/payments/{self.payment_uid}"))

        self.calls.clear()
        self.failures[upstream] = "timeout"
        with self.assertLogs("app.services.bookings", level="ERROR"):
            response = await self.client.post(route, json=self.data, headers=self.headers)
        self.assertEqual(response.status_code, 504)
        self.assertEqual(self.calls.count(upstream), 1)
        self.assertTrue(all(method != "DELETE" for _, method, _ in self.calls))

    async def test_failed_loyalty_registration_compensates_known_booking(self):
        loyalty = f"/internal/v1/loyalty/reservations/{self.reservation_uid}"
        self.failures[("loyalty", "PUT", loyalty)] = "timeout"
        response = await self.client.post("/api/v1/reservations", json=self.data, headers=self.headers)
        self.assertEqual(response.status_code, 503)
        self.assertEqual(self.calls[-3], ("reservation", "DELETE", f"/internal/v1/reservations/{self.reservation_uid}"))
        self.assertEqual(set(self.calls[-2:]), {
            ("payment", "DELETE", f"/internal/v1/payments/{self.payment_uid}"),
            ("loyalty", "DELETE", loyalty),
        })

    async def test_cancel_checks_owner_and_can_resume_after_failure(self):
        route = f"/api/v1/reservations/{self.reservation_uid}"
        reservation = f"/internal/v1/reservations/{self.reservation_uid}"
        owned = ("reservation", "GET", reservation)
        self.failures[owned] = 404
        response = await self.client.delete(route, headers=self.headers)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.calls, [owned])
        del self.failures[owned]

        payment = ("payment", "DELETE", f"/internal/v1/payments/{self.payment_uid}")
        self.failures[payment] = 503
        response = await self.client.delete(route, headers=self.headers)
        self.assertEqual(response.status_code, 503)
        self.assertEqual(self.calls, [owned, owned, payment])
        del self.failures[payment]
        response = await self.client.delete(route, headers=self.headers)
        self.assertEqual((response.status_code, response.content), (204, b""))
        self.assertEqual(self.calls[-3:], [
            payment, ("reservation", "DELETE", reservation),
            ("loyalty", "DELETE", f"/internal/v1/loyalty/reservations/{self.reservation_uid}"),
        ])

    async def test_invalid_upstream_payload_becomes_502(self):
        self.failures[("loyalty", "GET", "/internal/v1/loyalty")] = "malformed"
        response = await self.client.get("/api/v1/loyalty", headers=self.headers)
        self.assertEqual(response.status_code, 502)
        self.assertIn("message", response.json())

    async def test_read_fallback_is_local_to_the_failed_service(self):
        self.failures[("loyalty", "GET", "/internal/v1/loyalty")] = "disconnected"
        self.failures[("payment", "GET", f"/internal/v1/payments/{self.payment_uid}")] = "timeout"
        response = await self.client.get("/api/v1/me", headers=self.headers)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["loyalty"], {})
        self.assertEqual(response.json()["reservations"][0]["payment"], {})
        self.failures[("reservation", "GET", "/internal/v1/reservations")] = 503
        response = await self.client.get("/api/v1/me", headers=self.headers)
        self.assertEqual(response.status_code, 503)

    async def test_cancellation_queues_only_loyalty_and_retries(self):
        path = f"/api/v1/reservations/{self.reservation_uid}"
        loyalty = ("loyalty", "DELETE", f"/internal/v1/loyalty/reservations/{self.reservation_uid}")
        self.failures[loyalty] = "disconnected"
        response = await self.client.delete(path, headers=self.headers)
        self.assertEqual((response.status_code, response.content), (204, b""))
        self.calls.clear()
        worker = asyncio.create_task(self.retries.run())
        try:
            async with asyncio.timeout(1):
                while not self.calls:
                    await asyncio.sleep(0.005)
                del self.failures[loyalty]
                while len(self.calls) < 2:
                    await asyncio.sleep(0.005)
            self.assertEqual(self.calls, [loyalty, loyalty])
        finally:
            worker.cancel()
            await asyncio.gather(worker, return_exceptions=True)
