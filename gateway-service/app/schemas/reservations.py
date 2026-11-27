import re
from datetime import date
from typing import Annotated, Literal
from uuid import UUID

from pydantic import AfterValidator, BaseModel, BeforeValidator, ConfigDict, Field, ValidationInfo

from app.schemas.loyalty import LoyaltyInfoResponse


def _parse_date(value: object) -> date:
    if isinstance(value, str) and re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        return date.fromisoformat(value)
    raise ValueError("Дата должна быть в формате YYYY-MM-DD")


def _check_checkout(value: date, info: ValidationInfo) -> date:
    start = info.data.get("start_date") if info.data else None
    if start is not None and value <= start:
        raise ValueError("Дата выезда должна быть позже даты заезда")
    return value


BookingDate = Annotated[date, BeforeValidator(_parse_date)]
CheckoutDate = Annotated[BookingDate, AfterValidator(_check_checkout)]
ReservationStatus = Literal["PAID", "RESERVED", "CANCELED"]
PaymentStatus = Literal["PAID", "REVERSED", "CANCELED"]


class CreateReservationRequest(BaseModel):
    hotel_uid: UUID = Field(alias="hotelUid")
    start_date: BookingDate = Field(alias="startDate")
    end_date: CheckoutDate = Field(alias="endDate")


class HotelInfo(BaseModel):
    hotel_uid: UUID = Field(alias="hotelUid")
    name: str
    full_address: str = Field(alias="fullAddress")
    stars: int | None


class PaymentInfo(BaseModel):
    status: PaymentStatus
    price: int = Field(ge=0)


class ReservationFields(BaseModel):
    model_config = ConfigDict(validate_by_name=True)

    reservation_uid: UUID = Field(alias="reservationUid")
    start_date: date | None = Field(alias="startDate")
    end_date: date | None = Field(alias="endDate")
    status: ReservationStatus


class UnavailableDetails(BaseModel):
    """An empty object when optional upstream data is unavailable."""


class ReservationResponse(ReservationFields):
    hotel: HotelInfo
    payment: PaymentInfo | UnavailableDetails


class CreateReservationResponse(ReservationFields):
    hotel_uid: UUID = Field(alias="hotelUid")
    start_date: date = Field(alias="startDate")
    end_date: date = Field(alias="endDate")
    discount: int
    payment: PaymentInfo


class UserInfoResponse(BaseModel):
    reservations: list[ReservationResponse]
    loyalty: LoyaltyInfoResponse | UnavailableDetails
