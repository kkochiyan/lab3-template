from fastapi import APIRouter

from app.routers.dependencies import BookingDependency, UsernameHeader
from app.schemas.loyalty import LoyaltyInfoResponse
from app.schemas.reservations import UserInfoResponse

router = APIRouter(tags=["Users"])


@router.get("/me", response_model=UserInfoResponse)
async def get_me(username: UsernameHeader, service: BookingDependency) -> UserInfoResponse:
    return await service.get_user_info(username)


@router.get("/loyalty", response_model=LoyaltyInfoResponse)
async def get_loyalty(
    username: UsernameHeader, service: BookingDependency,
) -> LoyaltyInfoResponse:
    return await service.get_loyalty(username)
