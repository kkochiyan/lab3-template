from fastapi import APIRouter, Depends, Header, Path, Response
from fastapi.responses import JSONResponse

from uuid import UUID

from typing import Annotated

from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.services.reservations import ReservationService
from app.unit_of_work import ReservationUnitOfWork
from app.schemas.reservations import (
    InternalCreateReservationRequest,
    InternalReservationResponse,
)
from app.schemas.errors import ErrorResponse
from app.errors import HotelNotFound, ReservationNotFound

UsernameHeader = Annotated[
    str, Header(alias="X-User-Name", min_length=1, max_length=80, pattern=r"\S")
]

router = APIRouter(
    prefix="/reservations",
    tags=["Reservations"]
)

async def get_reservation_service(
        session: Annotated[AsyncSession, Depends(get_session)],
) -> ReservationService:
    return ReservationService(ReservationUnitOfWork(session))

@router.get(
    "",
    response_model=list[InternalReservationResponse]
)
async def get_reservations_by_username(
    reservation_service: Annotated[ReservationService, Depends(get_reservation_service)],
    username: UsernameHeader,
) -> list[InternalReservationResponse]:
    return await reservation_service.get_list_by_username(username=username)


@router.post(
    "",
    status_code=201,
    response_model=InternalReservationResponse,
    responses={404: {"model": ErrorResponse}},
)
async def create_reservation(
    request: InternalCreateReservationRequest,
    username: UsernameHeader,
    reservation_service: Annotated[ReservationService, Depends(get_reservation_service)],
) -> InternalReservationResponse | JSONResponse:
    try:
        return await reservation_service.create_reservation(
            username=username,
            request=request,
        )
    except HotelNotFound:
        error = ErrorResponse(message="Отель не найден")
        return JSONResponse(status_code=404, content=error.model_dump())


@router.get(
    "/{reservationUid}",
    response_model=InternalReservationResponse,
    responses={404: {"model": ErrorResponse}},
)
async def get_reservation_by_uid_and_username(
    reservation_uid: Annotated[UUID, Path(alias="reservationUid")],
    username: UsernameHeader,
    reservation_service: Annotated[ReservationService, Depends(get_reservation_service)]
) -> InternalReservationResponse | JSONResponse:
    try:
        return await reservation_service.get_reservation_by_uuid_username(username=username, reservation_uuid=reservation_uid)
    except ReservationNotFound:
        error = ErrorResponse(message="Бронирование не найдено")
        return JSONResponse(
            status_code=404,
            content=error.model_dump(),
        )


@router.delete(
    "/{reservationUid}",
    status_code=204,
    responses={404: {"model": ErrorResponse}}
)
async def cancel_reservation(
    reservation_uid: Annotated[UUID, Path(alias="reservationUid")],
    username: UsernameHeader,
    reservation_service: Annotated[
        ReservationService, Depends(get_reservation_service)
    ],
) -> Response:
    try:
        await reservation_service.cancel_reservation(
            username=username,
            reservation_uuid=reservation_uid,
        )
    except ReservationNotFound:
        error = ErrorResponse(message="Бронирование не найдено")
        return JSONResponse(status_code=404, content=error.model_dump())

    return Response(status_code=204)
