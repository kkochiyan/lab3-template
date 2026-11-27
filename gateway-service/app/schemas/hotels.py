from uuid import UUID

from pydantic import BaseModel, Field


class HotelResponse(BaseModel):
    hotel_uid: UUID = Field(alias="hotelUid")
    name: str
    country: str
    city: str
    address: str
    stars: int | None
    price: int


class PaginationResponse(BaseModel):
    page: int
    page_size: int = Field(alias="pageSize")
    total_elements: int = Field(alias="totalElements")
    items: list[HotelResponse]