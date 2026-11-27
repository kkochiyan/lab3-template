from sqlalchemy.ext.asyncio import AsyncSession, AsyncSessionTransaction

from app.repositories.hotels import HotelRepository
from app.repositories.reservations import ReservationRepository
from app.services.protocols import HotelReader, ReservationRepositoryProtocol


class ReservationUnitOfWork:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self.hotels: HotelReader = HotelRepository(session)
        self.reservations: ReservationRepositoryProtocol = ReservationRepository(session)

    def transaction(self) -> AsyncSessionTransaction:
        return self._session.begin()
