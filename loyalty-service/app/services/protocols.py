from typing import Protocol
from uuid import UUID

from app.models import Loyalty, LoyaltyReservation


class LoyaltyRepositoryProtocol(Protocol):
    async def get_by_username(self, *, username: str) -> Loyalty | None: ...

    async def get_or_create_for_update(self, *, username: str, discount: int) -> Loyalty: ...

    async def get_or_add_reservation(
        self, *, reservation_uid: UUID, username: str, active: bool
    ) -> tuple[LoyaltyReservation, bool]: ...
