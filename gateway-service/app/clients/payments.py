from uuid import UUID

import httpx
from pydantic import Field, TypeAdapter

from app.clients.http import ServiceClient
from app.schemas.reservations import PaymentInfo


class PaymentRecord(PaymentInfo):
    payment_uid: UUID = Field(alias="paymentUid")


_payment = TypeAdapter(PaymentRecord)


class PaymentClient(ServiceClient):
    def __init__(self, client: httpx.AsyncClient) -> None:
        super().__init__(client, "Payment")

    async def create_payment(self, price: int) -> PaymentRecord:
        response = await self._request("POST", "/internal/v1/payments", json={"price": price})
        return self._decode(response, _payment)

    async def get_payment(self, uid: UUID) -> PaymentRecord:
        return await self._read(f"/internal/v1/payments/{uid}", _payment)

    async def cancel_payment(self, uid: UUID) -> None:
        await self._request("DELETE", f"/internal/v1/payments/{uid}")
