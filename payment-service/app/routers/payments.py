from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Response
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.errors import PaymentNotFound
from app.schemas.errors import ErrorResponse
from app.schemas.payments import InternalCreatePaymentRequest, InternalPaymentResponse
from app.services.payments import PaymentService
from app.unit_of_work import PaymentUnitOfWork

router = APIRouter(prefix="/payments", tags=["Payments"])
PaymentUid = Annotated[UUID, Path(alias="paymentUid")]


async def get_payment_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> PaymentService:
    return PaymentService(PaymentUnitOfWork(session))


def _payment_not_found_response() -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content=ErrorResponse(message="Оплата не найдена").model_dump(),
    )


@router.post("", status_code=201, response_model=InternalPaymentResponse)
async def create_payment(
    request: InternalCreatePaymentRequest,
    payment_service: Annotated[PaymentService, Depends(get_payment_service)],
) -> InternalPaymentResponse:
    return await payment_service.create_payment(price=request.price)


@router.get(
    "/{paymentUid}",
    response_model=InternalPaymentResponse,
    responses={404: {"model": ErrorResponse}},
)
async def get_payment(
    payment_uid: PaymentUid,
    payment_service: Annotated[PaymentService, Depends(get_payment_service)],
) -> InternalPaymentResponse | JSONResponse:
    try:
        return await payment_service.get_payment(payment_uid=payment_uid)
    except PaymentNotFound:
        return _payment_not_found_response()


@router.delete("/{paymentUid}", status_code=204, responses={404: {"model": ErrorResponse}})
async def cancel_payment(
    payment_uid: PaymentUid,
    payment_service: Annotated[PaymentService, Depends(get_payment_service)],
) -> Response:
    try:
        await payment_service.cancel_payment(payment_uid=payment_uid)
    except PaymentNotFound:
        return _payment_not_found_response()
    return Response(status_code=204)
