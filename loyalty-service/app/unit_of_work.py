from sqlalchemy.ext.asyncio import AsyncSession, AsyncSessionTransaction

from app.repositories.loyalty import LoyaltyRepository
from app.services.protocols import LoyaltyRepositoryProtocol


class LoyaltyUnitOfWork:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self.loyalty: LoyaltyRepositoryProtocol = LoyaltyRepository(session)

    def transaction(self) -> AsyncSessionTransaction:
        return self._session.begin()
