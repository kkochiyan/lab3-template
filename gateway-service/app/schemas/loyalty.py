from typing import Literal

from pydantic import BaseModel, Field


class LoyaltyInfoResponse(BaseModel):
    status: Literal["BRONZE", "SILVER", "GOLD"]
    discount: int = Field(ge=0, le=100)
    reservation_count: int = Field(alias="reservationCount", ge=0)
