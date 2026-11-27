import re
from datetime import date
from typing import Self
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from app.schemas.hotels import HotelInfo
from app.enums import ReservationStatus


class InternalCreateReservationRequest(BaseModel):
    hotel_uid: UUID = Field(alias="hotelUid")
    payment_uid: UUID = Field(alias="paymentUid")
    start_date: date = Field(alias="startDate")
    end_date: date = Field(alias="endDate")

    @field_validator("start_date", "end_date", mode="before")
    @classmethod
    def validate_calendar_date(cls, value: object) -> date:
        if type(value) is date:
            return value
        if not isinstance(value, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
            raise ValueError("Дата должна быть в формате YYYY-MM-DD")
        return date.fromisoformat(value)

    @model_validator(mode="after")
    def validate_date_range(self) -> Self:
        if self.end_date <= self.start_date:
            raise ValueError("Дата выезда должна быть позже даты заезда")
        return self


class InternalReservationResponse(BaseModel):
    reservation_uid: UUID = Field(serialization_alias="reservationUid")
    hotel_info: HotelInfo = Field(serialization_alias="hotel")
    start_date: date | None = Field(serialization_alias="startDate")
    end_date: date | None = Field(serialization_alias="endDate")
    status: ReservationStatus
    payment_uid: UUID = Field(serialization_alias="paymentUid")
