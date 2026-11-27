from contextlib import asynccontextmanager
from pathlib import Path
from unittest import IsolatedAsyncioTestCase
from unittest.mock import patch
from uuid import uuid4

import httpx
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from app.base import Base
from app.database import get_session
from app.main import app


class SQLiteSessionAdapter:
    def __init__(self, session: Session) -> None:
        self.session = session

    async def execute(self, statement):
        return self.session.execute(statement)

    async def get(self, model, key):
        return self.session.get(model, key)

    @asynccontextmanager
    async def begin(self):
        with self.session.begin():
            yield


class LoyaltyApiTest(IsolatedAsyncioTestCase):
    path = "/internal/v1/loyalty"
    user = {"X-User-Name": "New User"}

    async def asyncSetUp(self):
        engine = create_engine("sqlite://")
        self.addCleanup(engine.dispose)

        @event.listens_for(engine, "connect")
        def enable_foreign_keys(connection, _):
            connection.execute("PRAGMA foreign_keys=ON")

        Base.metadata.create_all(engine)
        with engine.begin() as connection:
            connection.exec_driver_sql(
                (Path(__file__).resolve().parents[1] / "seed.sql").read_text(encoding="utf-8")
            )

        async def session_override():
            with Session(engine) as session:
                yield SQLiteSessionAdapter(session)

        overrides = patch.dict(app.dependency_overrides, {get_session: session_override})
        overrides.start()
        self.addCleanup(overrides.stop)
        self.client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        )
        self.addAsyncCleanup(self.client.aclose)

    def assert_loyalty(self, response, *, count, status, discount):
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(
            response.json(),
            {"reservationCount": count, "status": status, "discount": discount},
        )

    async def test_default_and_seed(self):
        self.assertEqual((await self.client.get("/manage/health")).status_code, 200)
        self.assert_loyalty(
            await self.client.get(self.path, headers=self.user),
            count=0, status="BRONZE", discount=5,
        )
        self.assert_loyalty(
            await self.client.get(self.path, headers={"X-User-Name": "Test Max"}),
            count=25, status="GOLD", discount=10,
        )

    async def test_promotions_and_demotions(self):
        bookings = [f"{self.path}/reservations/{uuid4()}" for _ in range(20)]
        for count, url in enumerate(bookings, 1):
            response = await self.client.put(url, headers=self.user)
            if count in (9, 10, 19, 20):
                status, discount = {
                    9: ("BRONZE", 5), 10: ("SILVER", 7),
                    19: ("SILVER", 7), 20: ("GOLD", 10),
                }[count]
                self.assert_loyalty(response, count=count, status=status, discount=discount)
            else:
                self.assertEqual(response.status_code, 200, response.text)
        for count, url in zip(range(19, 8, -1), reversed(bookings)):
            status, discount = ("SILVER", 7) if count >= 10 else ("BRONZE", 5)
            self.assert_loyalty(
                await self.client.delete(url, headers=self.user),
                count=count, status=status, discount=discount,
            )

    async def test_retries_and_early_cancellation(self):
        url = f"{self.path}/reservations/{uuid4()}"
        for method, count in (("PUT", 1), ("PUT", 1), ("DELETE", 0), ("DELETE", 0), ("PUT", 0)):
            self.assert_loyalty(
                await self.client.request(method, url, headers=self.user),
                count=count, status="BRONZE", discount=5,
            )
        url = f"{self.path}/reservations/{uuid4()}"
        for method in ("DELETE", "PUT"):
            self.assert_loyalty(
                await self.client.request(method, url, headers=self.user),
                count=0, status="BRONZE", discount=5,
            )

    async def test_owner_conflict_and_invalid_parameters(self):
        url = f"{self.path}/reservations/{uuid4()}"
        self.assertEqual((await self.client.put(url, headers=self.user)).status_code, 200)
        for method in ("PUT", "DELETE"):
            response = await self.client.request(method, url, headers={"X-User-Name": "Other"})
            self.assertEqual(response.status_code, 409)
        self.assert_loyalty(
            await self.client.get(self.path, headers=self.user),
            count=1, status="BRONZE", discount=5,
        )
        for headers in ({}, {"X-User-Name": "  "}, {"X-User-Name": "u" * 81}):
            self.assertEqual((await self.client.get(self.path, headers=headers)).status_code, 422)
        response = await self.client.put(f"{self.path}/reservations/bad", headers=self.user)
        self.assertEqual(response.status_code, 422)
