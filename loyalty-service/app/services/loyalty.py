from uuid import UUID

from app.enums import LoyaltyStatus
from app.errors import ReservationOwnerConflict
from app.schemas.loyalty import LoyaltyInfoResponse
from app.unit_of_work import LoyaltyUnitOfWork


def _loyalty_for_count(count: int) -> LoyaltyInfoResponse:
    if count >= 20:
        status, discount = LoyaltyStatus.GOLD, 10
    elif count >= 10:
        status, discount = LoyaltyStatus.SILVER, 7
    else:
        status, discount = LoyaltyStatus.BRONZE, 5

    return LoyaltyInfoResponse(status=status, discount=discount, reservation_count=count)


class LoyaltyService:
    def __init__(self, uow: LoyaltyUnitOfWork) -> None:
        self._uow = uow

    async def get_loyalty(self, *, username: str) -> LoyaltyInfoResponse:
        loyalty = await self._uow.loyalty.get_by_username(username=username)
        if loyalty is None:
            return _loyalty_for_count(0)
        return LoyaltyInfoResponse(
            status=loyalty.status, discount=loyalty.discount,
            reservation_count=loyalty.reservation_count,
        )

    async def set_reservation_state(
        self, *, username: str, reservation_uid: UUID, active: bool
    ) -> LoyaltyInfoResponse:
        async with self._uow.transaction():
            loyalty = await self._uow.loyalty.get_or_create_for_update(
                username=username, discount=_loyalty_for_count(0).discount,
            )
            reservation, created = await self._uow.loyalty.get_or_add_reservation(
                reservation_uid=reservation_uid, username=username, active=active,
            )
            if reservation.username != username:
                raise ReservationOwnerConflict()

            if created and active:
                loyalty.reservation_count += 1
            elif not active and reservation.active:
                reservation.active = False
                loyalty.reservation_count = max(loyalty.reservation_count - 1, 0)

            response = _loyalty_for_count(loyalty.reservation_count)
            loyalty.status = response.status
            loyalty.discount = response.discount

        return response
