from fastapi import APIRouter, Response

from app.routers.dependencies import BookingDependency, ReservationUid, UsernameHeader
from app.schemas.errors import ErrorResponse, ValidationErrorResponse
from app.schemas.reservations import (
    CreateReservationRequest,
    CreateReservationResponse,
    ReservationResponse,
)

router = APIRouter(prefix="/reservations", tags=["Reservations"])


@router.get("", response_model=list[ReservationResponse])
async def list_reservations(
    username: UsernameHeader, service: BookingDependency,
) -> list[ReservationResponse]:
    return await service.list_reservations(username)


@router.post(
    "",
    response_model=CreateReservationResponse,
    responses={400: {"model": ValidationErrorResponse}},
)
async def create_reservation(
    request: CreateReservationRequest, username: UsernameHeader, service: BookingDependency,
) -> CreateReservationResponse:
    return await service.create_reservation(username, request)


@router.get(
    "/{reservationUid}",
    response_model=ReservationResponse,
    responses={404: {"model": ErrorResponse}},
)
async def get_reservation(
    reservation_uid: ReservationUid, username: UsernameHeader, service: BookingDependency,
) -> ReservationResponse:
    return await service.get_reservation(username, reservation_uid)


@router.delete("/{reservationUid}", status_code=204, responses={404: {"model": ErrorResponse}})
async def cancel_reservation(
    reservation_uid: ReservationUid, username: UsernameHeader, service: BookingDependency,
) -> Response:
    await service.cancel_reservation(username, reservation_uid)
    return Response(status_code=204)
