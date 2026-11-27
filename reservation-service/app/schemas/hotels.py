from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

class HotelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    hotel_uid: UUID = Field(serialization_alias="hotelUid")
    name: str
    country: str
    city: str
    address: str
    stars: int | None
    price: int


class HotelsPageResponse(BaseModel):
    page: int
    page_size: int = Field(serialization_alias="pageSize")
    total_elements: int = Field(serialization_alias="totalElements")
    items: list[HotelResponse]


class HotelInfo(BaseModel):
    hotel_uid: UUID = Field(serialization_alias="hotelUid")
    name: str
    full_address: str = Field(serialization_alias="fullAddress")
    stars: int | None   