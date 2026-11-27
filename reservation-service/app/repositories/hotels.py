from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models import Hotel

class HotelRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_hotels_list(self, *, offset: int, limit: int) -> list[Hotel]:
        statement = (
            select(Hotel)
            .order_by(Hotel.id)
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.scalars(statement)
        return list(result.all())

    async def get_count_hotels(self) -> int:
        statement = select(func.count()).select_from(Hotel)
        result = await self._session.execute(statement)
        return result.scalar_one()

    async def get_by_uuid(self, hotel_uid: UUID) -> Hotel | None:
        statement = select(Hotel).where(Hotel.hotel_uid == hotel_uid)
        result = await self._session.execute(statement=statement)
        return result.scalar_one_or_none()