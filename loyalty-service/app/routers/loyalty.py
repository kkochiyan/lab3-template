from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Path
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.errors import ReservationOwnerConflict
from app.schemas.errors import ErrorResponse
from app.schemas.loyalty import LoyaltyInfoResponse
from app.services.loyalty import LoyaltyService
from app.unit_of_work import LoyaltyUnitOfWork

router = APIRouter(prefix="/loyalty", tags=["Loyalty"])
UsernameHeader = Annotated[
    str, Header(alias="X-User-Name", min_length=1, max_length=80, pattern=r"\S")
]
ReservationUid = Annotated[UUID, Path(alias="reservationUid")]


async def get_loyalty_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> LoyaltyService:
    return LoyaltyService(LoyaltyUnitOfWork(session))


LoyaltyDependency = Annotated[LoyaltyService, Depends(get_loyalty_service)]


@router.get("", response_model=LoyaltyInfoResponse)
async def get_loyalty(username: UsernameHeader, service: LoyaltyDependency) -> LoyaltyInfoResponse:
    return await service.get_loyalty(username=username)


async def _set_reservation_state(
    service: LoyaltyService, *, username: str, reservation_uid: UUID, active: bool
) -> LoyaltyInfoResponse | JSONResponse:
    try:
        return await service.set_reservation_state(
            username=username, reservation_uid=reservation_uid, active=active,
        )
    except ReservationOwnerConflict:
        error = ErrorResponse(message="Бронирование принадлежит другому пользователю")
        return JSONResponse(status_code=409, content=error.model_dump())


@router.put(
    "/reservations/{reservationUid}",
    response_model=LoyaltyInfoResponse,
    responses={409: {"model": ErrorResponse}},
)
async def register_reservation(
    reservation_uid: ReservationUid, username: UsernameHeader, service: LoyaltyDependency
) -> LoyaltyInfoResponse | JSONResponse:
    return await _set_reservation_state(
        service, username=username, reservation_uid=reservation_uid, active=True,
    )


@router.delete(
    "/reservations/{reservationUid}",
    response_model=LoyaltyInfoResponse,
    responses={409: {"model": ErrorResponse}},
)
async def cancel_reservation(
    reservation_uid: ReservationUid, username: UsernameHeader, service: LoyaltyDependency
) -> LoyaltyInfoResponse | JSONResponse:
    return await _set_reservation_state(
        service, username=username, reservation_uid=reservation_uid, active=False,
    )
