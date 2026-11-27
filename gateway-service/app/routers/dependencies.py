from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, Path, Request

from app.services.bookings import BookingService

UsernameHeader = Annotated[
    str, Header(alias="X-User-Name", min_length=1, max_length=80, pattern=r"\S")
]
ReservationUid = Annotated[UUID, Path(alias="reservationUid")]


async def get_booking_service(request: Request) -> BookingService:
    return request.app.state.booking_service


BookingDependency = Annotated[BookingService, Depends(get_booking_service)]
