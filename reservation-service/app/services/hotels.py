from uuid import UUID

from app.schemas.hotels import HotelResponse, HotelsPageResponse
from app.services.protocols import HotelReader
from app.errors import HotelNotFound

class HotelService:
    def __init__(self, repository: HotelReader) -> None:
        self._repository = repository

    async def get_hotels(self, page: int, size: int) -> HotelsPageResponse:
        offset = (max(page, 1) - 1) * size
        hotels = await self._repository.get_hotels_list(offset=offset, limit=size)
        total = await self._repository.get_count_hotels()

        return HotelsPageResponse(
            page=page,
            page_size=len(hotels),
            total_elements=total,
            items=[HotelResponse.model_validate(hotel) for hotel in hotels]
        )

    async def get_hotel(self, hotel_uid: UUID) -> HotelResponse:
        hotel = await self._repository.get_by_uuid(hotel_uid=hotel_uid)

        if hotel is None:
            raise HotelNotFound()

        return HotelResponse.model_validate(hotel)
