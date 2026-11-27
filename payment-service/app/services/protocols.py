from typing import Protocol
from uuid import UUID

from app.models import Payment


class PaymentRepositoryProtocol(Protocol):
    def add(self, payment: Payment) -> None: ...

    async def get_by_uid(self, *, payment_uid: UUID) -> Payment | None: ...

    async def cancel_by_uid(self, *, payment_uid: UUID) -> bool: ...
