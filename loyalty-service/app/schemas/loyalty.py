from pydantic import BaseModel, Field

from app.enums import LoyaltyStatus


class LoyaltyInfoResponse(BaseModel):
    status: LoyaltyStatus
    discount: int
    reservation_count: int = Field(serialization_alias="reservationCount")
