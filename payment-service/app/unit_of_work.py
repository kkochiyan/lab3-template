from sqlalchemy.ext.asyncio import AsyncSession, AsyncSessionTransaction

from app.repositories.payments import PaymentRepository
from app.services.protocols import PaymentRepositoryProtocol


class PaymentUnitOfWork:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self.payments: PaymentRepositoryProtocol = PaymentRepository(session)

    def transaction(self) -> AsyncSessionTransaction:
        return self._session.begin()
