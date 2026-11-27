from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.enums import PaymentStatus


class InternalCreatePaymentRequest(BaseModel):
    price: int = Field(strict=True, ge=0, le=2_147_483_647)


class InternalPaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    payment_uid: UUID = Field(serialization_alias="paymentUid")
    status: PaymentStatus
    price: int
