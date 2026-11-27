from contextlib import asynccontextmanager
from unittest import IsolatedAsyncioTestCase
from unittest.mock import patch
from uuid import uuid4

import httpx
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.base import Base
from app.database import get_session
from app.main import app
from app.models import Payment


class SQLiteSessionAdapter:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, instance):
        self.session.add(instance)

    async def execute(self, statement):
        return self.session.execute(statement)

    @asynccontextmanager
    async def begin(self):
        with self.session.begin():
            yield


class PaymentsApiTest(IsolatedAsyncioTestCase):
    payments = "/internal/v1/payments"

    async def asyncSetUp(self):
        self.engine = create_engine("sqlite://")
        self.addCleanup(self.engine.dispose)
        Base.metadata.create_all(self.engine)

        async def session_override():
            with Session(self.engine, expire_on_commit=False) as session:
                yield SQLiteSessionAdapter(session)

        overrides = patch.dict(app.dependency_overrides, {get_session: session_override})
        overrides.start()
        self.addCleanup(overrides.stop)
        self.client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        )
        self.addAsyncCleanup(self.client.aclose)

    async def test_create_read_and_cancel(self):
        self.assertEqual((await self.client.get("/manage/health")).status_code, 200)
        response = await self.client.post(self.payments, json={"price": 27000})
        self.assertEqual(response.status_code, 201, response.text)
        data = response.json()
        self.assertEqual(data["price"], 27000)
        self.assertEqual(data["status"], "PAID")
        url = f"{self.payments}/{data['paymentUid']}"

        response = await self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), data)
        for _ in range(2):
            response = await self.client.delete(url)
            self.assertEqual((response.status_code, response.content), (204, b""))
        response = await self.client.get(url)
        self.assertEqual(response.json(), data | {"status": "CANCELED"})

    async def test_unknown_and_invalid_payment_uid(self):
        for method in ("GET", "DELETE"):
            response = await self.client.request(method, f"{self.payments}/{uuid4()}")
            self.assertEqual(response.status_code, 404)
            self.assertEqual(response.json(), {"message": "Оплата не найдена"})
            response = await self.client.request(method, f"{self.payments}/not-a-uuid")
            self.assertEqual(response.status_code, 422)

    async def test_invalid_price_does_not_create_payment(self):
        for payload in ({}, {"price": -1}, {"price": 8.5}, {"price": True}, {"price": 2**31}):
            with self.subTest(payload=payload):
                response = await self.client.post(self.payments, json=payload)
                self.assertEqual(response.status_code, 422)
        with Session(self.engine) as session:
            self.assertIsNone(session.scalar(select(Payment.id)))
