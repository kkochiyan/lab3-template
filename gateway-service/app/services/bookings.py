import asyncio
import logging
from collections.abc import Awaitable
from uuid import UUID

from app.clients.loyalty import LoyaltyClient
from app.clients.payments import PaymentClient
from app.clients.reservations import ReservationClient, ReservationRecord
from app.errors import GatewayError, InvalidBooking, ServiceUnavailable, UpstreamError
from app.resilience.loyalty_retry import LoyaltyCancellationQueue
from app.schemas.loyalty import LoyaltyInfoResponse
from app.schemas.reservations import (
    CreateReservationRequest,
    CreateReservationResponse,
    PaymentInfo,
    ReservationResponse,
    UnavailableDetails,
    UserInfoResponse,
)

logger = logging.getLogger(__name__)


class BookingService:
    def __init__(
        self, reservations: ReservationClient, payments: PaymentClient, loyalty: LoyaltyClient,
        loyalty_retries: LoyaltyCancellationQueue,
    ) -> None:
        self._reservations = reservations
        self._payments = payments
        self._loyalty = loyalty
        self._loyalty_retries = loyalty_retries
        self._payment_reads = asyncio.Semaphore(10)

    async def get_loyalty(self, username: str) -> LoyaltyInfoResponse:
        return await self._loyalty.get_loyalty(username)

    async def get_user_info(self, username: str) -> UserInfoResponse:
        reservations, loyalty = await asyncio.gather(
            self.list_reservations(username), self._get_optional_loyalty(username),
        )
        return UserInfoResponse(reservations=reservations, loyalty=loyalty)

    async def _get_optional_loyalty(self, username: str) -> LoyaltyInfoResponse | UnavailableDetails:
        try:
            return await self.get_loyalty(username)
        except UpstreamError as exc:
            if exc.rejected:
                raise
            return UnavailableDetails()

    async def list_reservations(self, username: str) -> list[ReservationResponse]:
        records = await self._reservations.list_reservations(username)
        return await asyncio.gather(*(self._with_payment(record) for record in records))

    async def get_reservation(self, username: str, uid: UUID) -> ReservationResponse:
        return await self._with_payment(await self._get_owned_reservation(username, uid))

    async def _get_owned_reservation(self, username: str, uid: UUID) -> ReservationRecord:
        try:
            return await self._reservations.get_reservation(username, uid)
        except UpstreamError as exc:
            if exc.upstream_status == 404:
                raise GatewayError(404, "Бронирование не найдено") from exc
            raise

    async def _with_payment(self, record: ReservationRecord) -> ReservationResponse:
        payment: PaymentInfo | UnavailableDetails
        try:
            async with self._payment_reads:
                details = await self._payments.get_payment(record.payment_uid)
            payment = PaymentInfo(status=details.status, price=details.price)
        except UpstreamError as exc:
            if exc.rejected and exc.upstream_status != 404:
                raise
            payment = UnavailableDetails()
        return ReservationResponse(
            reservation_uid=record.reservation_uid,
            hotel=record.hotel,
            start_date=record.start_date,
            end_date=record.end_date,
            status=record.status,
            payment=payment,
        )

    async def create_reservation(
        self, username: str, request: CreateReservationRequest
    ) -> CreateReservationResponse:
        try:
            hotel = await self._reservations.get_hotel(request.hotel_uid)
        except UpstreamError as exc:
            if exc.upstream_status == 404:
                raise InvalidBooking("hotelUid", "Отель не найден") from exc
            raise

        loyalty = await self._loyalty.get_loyalty(username)
        nights = (request.end_date - request.start_date).days
        # Payment stores integer prices. Round half up in the same monetary units.
        price = (hotel.price * nights * (100 - loyalty.discount) + 50) // 100
        if not 0 <= price <= 2_147_483_647:
            raise InvalidBooking("endDate", "Стоимость бронирования вне допустимого диапазона")

        payment = await self._payments.create_payment(price)
        try:
            record = await self._reservations.create_reservation(
                username, request, payment.payment_uid,
            )
        except UpstreamError as exc:
            if exc.rejected:
                await self._compensate("payment", payment.payment_uid, self._payments.cancel_payment(payment.payment_uid))
            else:
                logger.error("Unconfirmed reservation creation for payment %s", payment.payment_uid)
            if exc.upstream_status == 404:
                raise InvalidBooking("hotelUid", "Отель не найден") from exc
            raise

        try:
            await self._loyalty.register_reservation(username, record.reservation_uid)
        except UpstreamError:
            await self._compensate_booking(username, record)
            raise

        return CreateReservationResponse(
            reservation_uid=record.reservation_uid,
            hotel_uid=hotel.hotel_uid,
            start_date=request.start_date,
            end_date=request.end_date,
            discount=loyalty.discount,
            status=record.status,
            payment=PaymentInfo(status=payment.status, price=payment.price),
        )

    async def cancel_reservation(self, username: str, uid: UUID) -> None:
        record = await self._get_owned_reservation(username, uid)
        await self._payments.cancel_payment(record.payment_uid)
        await self._reservations.cancel_reservation(username, uid)
        await self._cancel_loyalty_or_queue(username, uid)

    async def _cancel_loyalty_or_queue(self, username: str, uid: UUID) -> None:
        try:
            await self._loyalty.cancel_reservation(username, uid)
        except ServiceUnavailable:
            self._loyalty_retries.enqueue(username, uid)

    async def _compensate_booking(self, username: str, record: ReservationRecord) -> None:
        uid = record.reservation_uid
        # Keep the payment active if cancellation of the booking cannot be confirmed.
        if await self._compensate("reservation", uid, self._reservations.cancel_reservation(username, uid)):
            await asyncio.gather(
                self._compensate("payment", record.payment_uid, self._payments.cancel_payment(record.payment_uid)),
                self._compensate("loyalty", uid, self._cancel_loyalty_or_queue(username, uid)),
            )

    @staticmethod
    async def _compensate(operation: str, uid: UUID, request: Awaitable[None]) -> bool:
        try:
            await request
            return True
        except UpstreamError:
            logger.exception("Compensation failed for %s %s", operation, uid)
            return False
