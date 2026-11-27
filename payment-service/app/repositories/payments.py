from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums import PaymentStatus
from app.models import Payment


class PaymentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(self, payment: Payment) -> None:
        self._session.add(payment)

    async def get_by_uid(self, *, payment_uid: UUID) -> Payment | None:
        statement = select(Payment).where(Payment.payment_uid == payment_uid)
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def cancel_by_uid(self, *, payment_uid: UUID) -> bool:
        statement = (
            update(Payment)
            .where(Payment.payment_uid == payment_uid, Payment.status == PaymentStatus.PAID)
            .values(status=PaymentStatus.CANCELED)
            .returning(Payment.id)
        )
        result = await self._session.execute(statement)
        if result.scalar_one_or_none() is not None:
            return True

        return await self.get_by_uid(payment_uid=payment_uid) is not None
