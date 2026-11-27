from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Loyalty, LoyaltyReservation


class LoyaltyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_username(self, *, username: str) -> Loyalty | None:
        statement = select(Loyalty).where(Loyalty.username == username)
        return (await self._session.execute(statement)).scalar_one_or_none()

    async def get_or_create_for_update(self, *, username: str, discount: int) -> Loyalty:
        statement = (
            insert(Loyalty)
            .values(username=username, discount=discount)
            .on_conflict_do_nothing(index_elements=[Loyalty.username])
        )
        await self._session.execute(statement)
        locked = select(Loyalty).where(Loyalty.username == username).with_for_update()
        return (await self._session.execute(locked)).scalar_one()

    async def get_or_add_reservation(
        self, *, reservation_uid: UUID, username: str, active: bool
    ) -> tuple[LoyaltyReservation, bool]:
        statement = (
            insert(LoyaltyReservation)
            .values(reservation_uid=reservation_uid, username=username, active=active)
            .on_conflict_do_nothing(index_elements=[LoyaltyReservation.reservation_uid])
            .returning(LoyaltyReservation)
        )
        added = (await self._session.execute(statement)).scalar_one_or_none()
        if added is not None:
            return added, True

        existing = await self._session.get(LoyaltyReservation, reservation_uid)
        if existing is None:
            raise RuntimeError("Reservation entry disappeared during the transaction")
        return existing, False
