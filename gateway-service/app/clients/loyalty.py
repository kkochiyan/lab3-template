from uuid import UUID

import httpx
from pydantic import TypeAdapter

from app.clients.http import ServiceClient, username_headers
from app.schemas.loyalty import LoyaltyInfoResponse

_loyalty = TypeAdapter(LoyaltyInfoResponse)


class LoyaltyClient(ServiceClient):
    def __init__(self, client: httpx.AsyncClient) -> None:
        super().__init__(client, "Loyalty")

    async def get_loyalty(self, username: str) -> LoyaltyInfoResponse:
        return await self._read("/internal/v1/loyalty", _loyalty, headers=username_headers(username))

    async def register_reservation(self, username: str, uid: UUID) -> None:
        await self._request(
            "PUT", f"/internal/v1/loyalty/reservations/{uid}", headers=username_headers(username),
        )

    async def cancel_reservation(self, username: str, uid: UUID) -> None:
        await self._request(
            "DELETE", f"/internal/v1/loyalty/reservations/{uid}", headers=username_headers(username),
        )
