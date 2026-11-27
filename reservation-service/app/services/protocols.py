from uuid import UUID

from typing import Protocol

from sqlalchemy import RowMapping

from app.models import Hotel, Reservation

class HotelReader(Protocol):
    async def get_hotels_list(self, *, offset: int, limit: int) -> list[Hotel]:
        ...

    async def get_count_hotels(self) -> int:
        ...

    async def get_by_uuid(self, *, hotel_uid: UUID) -> Hotel | None:
        ...


class ReservationRepositoryProtocol(Protocol):
    def add(self, reservation: Reservation) -> None:
        ...

    async def get_list_by_username(self, *, username: str) -> list[RowMapping]:
        ...

    async def get_by_reservation_uuid_and_username(self, *, username: str, reservation_uuid: UUID) -> RowMapping | None:
        ...

    async def cancel_by_uid(self, *, username: str, reservation_uuid: UUID) -> bool:
        ...
