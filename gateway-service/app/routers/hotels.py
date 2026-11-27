from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from app.schemas.hotels import PaginationResponse
from app.clients.reservations import ReservationClient

router = APIRouter(
    prefix="/hotels",
    tags=["Hotels"],
)

async def get_reservation_client(request: Request) -> ReservationClient:
    return request.app.state.reservation_client

@router.get(
    "",
    response_model=PaginationResponse,
)
async def get_hotels(
    client: Annotated[ReservationClient, Depends(get_reservation_client)],
    page: Annotated[int, Query(ge=0)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 10,
) -> PaginationResponse:
    return await client.get_hotels(page=page, size=size)
