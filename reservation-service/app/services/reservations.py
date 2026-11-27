from datetime import date, datetime, time, timezone
from uuid import UUID, uuid4

from sqlalchemy import RowMapping

from app.enums import ReservationStatus
from app.errors import HotelNotFound, ReservationNotFound
from app.models import Reservation
from app.schemas.hotels import HotelInfo
from app.schemas.reservations import (
    InternalCreateReservationRequest,
    InternalReservationResponse,
)
from app.unit_of_work import ReservationUnitOfWork


def _to_calendar_date(value: datetime | None) -> date | None:
    if value is None:
        return None
    if value.tzinfo is not None:
        value = value.astimezone(timezone.utc)
    return value.date()


class ReservationService:
    def __init__(self, uow: ReservationUnitOfWork) -> None:
        self._uow = uow

    async def create_reservation(
        self, *, username: str, request: InternalCreateReservationRequest
    ) -> InternalReservationResponse:
        async with self._uow.transaction():
            hotel = await self._uow.hotels.get_by_uuid(hotel_uid=request.hotel_uid)
            if hotel is None:
                raise HotelNotFound()

            reservation = Reservation(
                reservation_uid=uuid4(),
                username=username,
                payment_uid=request.payment_uid,
                hotel_id=hotel.id,
                status=ReservationStatus.PAID,
                start_date=datetime.combine(request.start_date, time.min, timezone.utc),
                end_date=datetime.combine(request.end_date, time.min, timezone.utc),
            )
            self._uow.reservations.add(reservation)
            response = InternalReservationResponse(
                reservation_uid=reservation.reservation_uid,
                hotel_info=HotelInfo(
                    hotel_uid=hotel.hotel_uid,
                    name=hotel.name,
                    full_address=f"{hotel.country}, {hotel.city}, {hotel.address}",
                    stars=hotel.stars,
                ),
                start_date=request.start_date,
                end_date=request.end_date,
                status=ReservationStatus.PAID,
                payment_uid=reservation.payment_uid,
            )

        return response

    async def get_list_by_username(self, username: str) -> list[InternalReservationResponse]:
        rows = await self._uow.reservations.get_list_by_username(username=username)
        return [self._to_response(row) for row in rows]

    async def get_reservation_by_uuid_username(
        self, 
        username: str, 
        reservation_uuid: UUID
    ) -> InternalReservationResponse:
        row = await self._uow.reservations.get_by_reservation_uuid_and_username(
            username=username,
            reservation_uuid=reservation_uuid
        )

        if row is None:
            raise ReservationNotFound()

        return self._to_response(row)

    async def cancel_reservation(
        self, *,
        username: str,
        reservation_uuid: UUID,
    ) -> None:
        async with self._uow.transaction():
            found = await self._uow.reservations.cancel_by_uid(
                username=username,
                reservation_uuid=reservation_uuid,
            )
            if not found:
                raise ReservationNotFound()
    
    @staticmethod
    def _to_response(row: RowMapping) -> InternalReservationResponse:
        return InternalReservationResponse(
            reservation_uid=row["reservation_uid"],
            hotel_info=HotelInfo(
                hotel_uid=row["hotel_uid"],
                name=row["name"],
                full_address=f'{row["country"]}, {row["city"]}, {row["address"]}',
                stars=row["stars"],
            ),
            start_date=_to_calendar_date(row["start_date"]),
            end_date=_to_calendar_date(row["end_date"]),
            status=row["status"],
            payment_uid=row["payment_uid"],
        )
