from uuid import UUID

import httpx
from pydantic import Field, TypeAdapter

from app.clients.http import ServiceClient, username_headers
from app.schemas.hotels import HotelResponse, PaginationResponse
from app.schemas.reservations import CreateReservationRequest, HotelInfo, ReservationFields


class ReservationRecord(ReservationFields):
    hotel: HotelInfo
    payment_uid: UUID = Field(alias="paymentUid")


_page = TypeAdapter(PaginationResponse)
_hotel = TypeAdapter(HotelResponse)
_reservation = TypeAdapter(ReservationRecord)
_reservations = TypeAdapter(list[ReservationRecord])


class ReservationClient(ServiceClient):
    def __init__(self, client: httpx.AsyncClient) -> None:
        super().__init__(client, "Reservation")

    async def get_hotels(self, *, page: int, size: int) -> PaginationResponse:
        return await self._read("/internal/v1/hotels", _page, params={"page": page, "size": size})

    async def get_hotel(self, hotel_uid: UUID) -> HotelResponse:
        return await self._read(f"/internal/v1/hotels/{hotel_uid}", _hotel)

    async def list_reservations(self, username: str) -> list[ReservationRecord]:
        return await self._read("/internal/v1/reservations", _reservations, headers=username_headers(username))

    async def get_reservation(self, username: str, uid: UUID) -> ReservationRecord:
        return await self._read(f"/internal/v1/reservations/{uid}", _reservation, headers=username_headers(username))

    async def create_reservation(
        self, username: str, request: CreateReservationRequest, payment_uid: UUID
    ) -> ReservationRecord:
        payload = request.model_dump(mode="json", by_alias=True)
        payload["paymentUid"] = str(payment_uid)
        response = await self._request(
            "POST", "/internal/v1/reservations", headers=username_headers(username), json=payload,
        )
        return self._decode(response, _reservation)

    async def cancel_reservation(self, username: str, uid: UUID) -> None:
        await self._request(
            "DELETE", f"/internal/v1/reservations/{uid}", headers=username_headers(username),
        )
