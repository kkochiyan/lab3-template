from contextlib import asynccontextmanager
from unittest import IsolatedAsyncioTestCase
from unittest.mock import patch
from uuid import uuid4

import httpx
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session

from app.base import Base
from app.database import get_session
from app.main import app
from app.models import Hotel, Reservation


class SQLiteSessionAdapter:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, instance):
        self.session.add(instance)

    async def execute(self, statement):
        return self.session.execute(statement)

    async def scalars(self, statement):
        return self.session.scalars(statement)

    @asynccontextmanager
    async def begin(self):
        with self.session.begin():
            yield


class ReservationApiTest(IsolatedAsyncioTestCase):
    hotels = "/internal/v1/hotels"
    reservations = "/internal/v1/reservations"
    owner = {"X-User-Name": "Test Max"}
    other_user = {"X-User-Name": "Other User"}

    async def asyncSetUp(self):
        self.engine = create_engine("sqlite://")
        self.addCleanup(self.engine.dispose)
        Base.metadata.create_all(self.engine)
        self.hotel_uid = uuid4()
        with Session(self.engine) as session:
            for uid, name in [(self.hotel_uid, "First"), (uuid4(), "Second")]:
                session.add(Hotel(
                    hotel_uid=uid, name=name, country="Россия", city="Москва",
                    address="Улица 1", stars=5, price=10000,
                ))
            session.commit()

        async def session_override():
            with Session(self.engine) as session:
                yield SQLiteSessionAdapter(session)

        overrides = patch.dict(app.dependency_overrides, {get_session: session_override})
        overrides.start()
        self.addCleanup(overrides.stop)
        self.client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
        )
        self.addAsyncCleanup(self.client.aclose)
        self.payload = {
            "hotelUid": str(self.hotel_uid),
            "paymentUid": str(uuid4()),
            "startDate": "2021-10-08",
            "endDate": "2021-10-11",
        }

    async def test_health_and_hotel_lookup(self):
        self.assertEqual((await self.client.get("/manage/health")).status_code, 200)
        first_pages = []
        for page in (0, 1, 2, 3):
            response = await self.client.get(self.hotels, params={"page": page, "size": 1})
            self.assertEqual(response.status_code, 200, response.text)
            body = response.json()
            self.assertEqual(body["page"], page)
            self.assertEqual(body["totalElements"], 2)
            self.assertEqual(body["pageSize"], len(body["items"]))
            first_pages.append([hotel["name"] for hotel in body["items"]])
        self.assertEqual(first_pages, [["First"], ["First"], ["Second"], []])
        self.assertEqual((await self.client.get(self.hotels, params={"size": 101})).status_code, 422)
        hotel = await self.client.get(f"{self.hotels}/{self.hotel_uid}")
        self.assertEqual(hotel.json()["price"], 10000)
        self.assertEqual((await self.client.get(f"{self.hotels}/{uuid4()}")).status_code, 404)
        self.assertEqual((await self.client.get(f"{self.hotels}/bad")).status_code, 422)

    async def test_create_read_and_cancel_as_owner(self):
        response = await self.client.post(self.reservations, json=self.payload, headers=self.owner)
        self.assertEqual(response.status_code, 201, response.text)
        booking = response.json()
        self.assertEqual(booking["status"], "PAID")
        self.assertEqual(booking["paymentUid"], self.payload["paymentUid"])
        self.assertEqual(booking["startDate"], self.payload["startDate"])
        self.assertEqual(booking["endDate"], self.payload["endDate"])
        self.assertEqual(booking["hotel"]["fullAddress"], "Россия, Москва, Улица 1")
        item = f"{self.reservations}/{booking['reservationUid']}"
        self.assertEqual((await self.client.get(item, headers=self.owner)).json(), booking)
        self.assertEqual((await self.client.get(self.reservations, headers=self.owner)).json(), [booking])
        self.assertEqual((await self.client.get(self.reservations, headers=self.other_user)).json(), [])
        for method in ("GET", "DELETE"):
            response = await self.client.request(method, item, headers=self.other_user)
            self.assertEqual(response.status_code, 404)
            self.assertEqual(response.json(), {"message": "Бронирование не найдено"})
        self.assertEqual((await self.client.get(item, headers=self.owner)).json()["status"], "PAID")
        for _ in range(2):
            response = await self.client.delete(item, headers=self.owner)
            self.assertEqual((response.status_code, response.content), (204, b""))
        with Session(self.engine) as session:
            self.assertEqual(session.scalar(select(Reservation.status)), "CANCELED")

    async def test_invalid_creation_leaves_database_empty(self):
        cases = [
            ({"startDate": "2021-02-30"}, self.owner, 422),
            ({"startDate": "2021-10-08T00:00:00Z"}, self.owner, 422),
            ({"startDate": 0}, self.owner, 422),
            ({"endDate": "2021-10-08"}, self.owner, 422),
            ({"endDate": "2021-10-07"}, self.owner, 422),
            ({"paymentUid": "bad"}, self.owner, 422),
            ({"hotelUid": str(uuid4())}, self.owner, 404),
            ({}, {}, 422),
            ({}, {"X-User-Name": "  "}, 422),
            ({}, {"X-User-Name": "x" * 81}, 422),
        ]
        for fields, headers, expected in cases:
            with self.subTest(fields=fields, expected=expected):
                response = await self.client.post(
                    self.reservations, json=self.payload | fields, headers=headers,
                )
                self.assertEqual(response.status_code, expected, response.text)
        with Session(self.engine) as session:
            self.assertIsNone(session.scalar(select(Reservation.id)))

    async def test_create_rolls_back_after_database_write(self):
        def fail_before_commit(session):
            session.flush()
            raise RuntimeError("forced failure after insert")

        event.listen(Session, "before_commit", fail_before_commit)
        try:
            with self.assertRaisesRegex(RuntimeError, "forced failure after insert"):
                await self.client.post(self.reservations, json=self.payload, headers=self.owner)
        finally:
            event.remove(Session, "before_commit", fail_before_commit)

        with Session(self.engine) as session:
            self.assertIsNone(session.scalar(select(Reservation.id)))
