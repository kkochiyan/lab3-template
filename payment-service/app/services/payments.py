from uuid import UUID, uuid4

from app.enums import PaymentStatus
from app.errors import PaymentNotFound
from app.models import Payment
from app.schemas.payments import InternalPaymentResponse
from app.unit_of_work import PaymentUnitOfWork


class PaymentService:
    def __init__(self, uow: PaymentUnitOfWork) -> None:
        self._uow = uow

    async def create_payment(self, *, price: int) -> InternalPaymentResponse:
        payment = Payment(payment_uid=uuid4(), status=PaymentStatus.PAID, price=price)
        async with self._uow.transaction():
            self._uow.payments.add(payment)
        return InternalPaymentResponse.model_validate(payment)

    async def get_payment(self, *, payment_uid: UUID) -> InternalPaymentResponse:
        payment = await self._uow.payments.get_by_uid(payment_uid=payment_uid)
        if payment is None:
            raise PaymentNotFound()
        return InternalPaymentResponse.model_validate(payment)

    async def cancel_payment(self, *, payment_uid: UUID) -> None:
        async with self._uow.transaction():
            if not await self._uow.payments.cancel_by_uid(payment_uid=payment_uid):
                raise PaymentNotFound()
