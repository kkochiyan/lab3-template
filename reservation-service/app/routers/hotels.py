from typing import Annotated
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import APIRouter, Depends, Query, Path
from fastapi.responses import JSONResponse

from app.schemas.hotels import HotelsPageResponse, HotelResponse
from app.schemas.errors import ErrorResponse
from app.database import get_session
from app.repositories.hotels import HotelRepository
from app.services.hotels import HotelService
from app.errors import HotelNotFound


router = APIRouter(
    prefix='/hotels',
    tags=["Hotels"]
)


async def get_hotel_service(
    session: Annotated[AsyncSession, Depends(get_session)]
) -> HotelService:
    return HotelService(HotelRepository(session=session))


@router.get(
    "",
    response_model=HotelsPageResponse
)
async def get_hotels(
    hotel_service: Annotated[HotelService, Depends(get_hotel_service)],
    page: Annotated[
        int, Query(ge=0, description="Нумерация с 1. Значение 0 — псевдоним первой страницы.")
    ] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 10,
) -> HotelsPageResponse:
    return await hotel_service.get_hotels(page=page, size=size)


@router.get(
    "/{hotelUid}",
    response_model=HotelResponse,
    responses={404: {"model": ErrorResponse}}
)
async def get_hotel_by_uid(
    hotel_service: Annotated[HotelService, Depends(get_hotel_service)],
    hotel_uid: Annotated[UUID, Path(alias="hotelUid")]
) -> HotelResponse | JSONResponse:
    try:
        return await hotel_service.get_hotel(hotel_uid=hotel_uid)
    except HotelNotFound:
        error = ErrorResponse(message="Отель не найден")
        return JSONResponse(status_code=404, content=error.model_dump())
