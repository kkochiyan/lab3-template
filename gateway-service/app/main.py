import asyncio
from contextlib import AsyncExitStack, asynccontextmanager, suppress

import httpx
from fastapi import FastAPI, Request
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.clients.loyalty import LoyaltyClient
from app.clients.payments import PaymentClient
from app.clients.reservations import ReservationClient
from app.config import settings
from app.errors import GatewayError, InvalidBooking
from app.resilience.loyalty_retry import LoyaltyCancellationQueue
from app.routers.hotels import router as hotel_router
from app.routers.reservations import router as reservation_router
from app.routers.users import router as user_router
from app.schemas.errors import ErrorDescription, ErrorResponse, ValidationErrorResponse
from app.services.bookings import BookingService


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with AsyncExitStack() as stack:
        reservations = await stack.enter_async_context(
            httpx.AsyncClient(base_url=settings.reservation_service_base_url, timeout=3.0)
        )
        payments = await stack.enter_async_context(
            httpx.AsyncClient(base_url=settings.payment_service_base_url, timeout=3.0)
        )
        loyalty = await stack.enter_async_context(
            httpx.AsyncClient(base_url=settings.loyalty_service_base_url, timeout=3.0)
        )
        app.state.reservation_client = ReservationClient(reservations)
        loyalty_client = LoyaltyClient(loyalty)
        retries = LoyaltyCancellationQueue(loyalty_client.cancel_reservation)
        app.state.booking_service = BookingService(
            app.state.reservation_client, PaymentClient(payments), loyalty_client, retries,
        )
        worker = asyncio.create_task(retries.run())
        try:
            yield
        finally:
            worker.cancel()
            with suppress(asyncio.CancelledError):
                await worker


app = FastAPI(title="API Gateway", lifespan=lifespan)
for router in (hotel_router, reservation_router, user_router):
    app.include_router(router, prefix="/api/v1")


@app.exception_handler(GatewayError)
async def handle_gateway_error(_: Request, exc: GatewayError) -> JSONResponse:
    if isinstance(exc, InvalidBooking):
        body = ValidationErrorResponse(
            message=exc.message,
            errors=[ErrorDescription(field=exc.field, error=exc.error)],
        )
    else:
        body = ErrorResponse(message=exc.message)
    return JSONResponse(status_code=exc.status_code, content=body.model_dump())


@app.exception_handler(RequestValidationError)
async def handle_request_validation(request: Request, exc: RequestValidationError) -> JSONResponse:
    if request.method != "POST" or request.url.path.rstrip("/") != "/api/v1/reservations":
        return await request_validation_exception_handler(request, exc)

    errors = [
        ErrorDescription(
            field=".".join(map(str, error["loc"][1:])) or str(error["loc"][0]),
            error=error["msg"],
        )
        for error in exc.errors()
    ]
    body = ValidationErrorResponse(message="Ошибка валидации данных", errors=errors)
    return JSONResponse(status_code=400, content=body.model_dump())


@app.get("/manage/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
