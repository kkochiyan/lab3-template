from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, RowMapping, Select, update

from app.models import Reservation, Hotel
from app.enums import ReservationStatus

class ReservationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(self, reservation: Reservation) -> None:
        self._session.add(reservation)

    def _select_with_hotel(self) -> Select:
        return (
            select (
                Reservation.reservation_uid, 
                Hotel.hotel_uid,
                Hotel.name,
                Hotel.address,
                Hotel.stars,
                Reservation.start_date,
                Reservation.end_date,
                Reservation.status, 
                Reservation.payment_uid,
                Hotel.country,
                Hotel.city
            ).select_from(Reservation)
            .join(Hotel, Reservation.hotel_id == Hotel.id)
        )

    async def get_list_by_username(self, username: str) -> list[RowMapping]:
        statement = self._select_with_hotel().where(
            Reservation.username == username
        ).order_by(Reservation.id)

        result = await self._session.execute(statement)
        return list(result.mappings().all())

    async def get_by_reservation_uuid_and_username(
            self, 
            username: str, 
            reservation_uuid: UUID
        ) -> RowMapping | None:
        statement = self._select_with_hotel().where(
            Reservation.username == username,
            Reservation.reservation_uid == reservation_uuid
        )

        result = await self._session.execute(statement)
        return result.mappings().one_or_none()

    async def cancel_by_uid(
        self, *, username: str, reservation_uuid: UUID
    ) -> bool:
        statement = (
            update(Reservation)
            .where(
                Reservation.reservation_uid == reservation_uuid,
                Reservation.username == username,
                Reservation.status == ReservationStatus.PAID,
            )
            .values(status=ReservationStatus.CANCELED)
            .returning(Reservation.id)
        )

        result = await self._session.execute(statement=statement)

        if result.scalar_one_or_none() is not None:
            return True

        existing = await self.get_by_reservation_uuid_and_username(
            username=username,
            reservation_uuid=reservation_uuid,
        )

        return existing is not None
