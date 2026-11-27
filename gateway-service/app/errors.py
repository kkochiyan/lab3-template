class GatewayError(Exception):
    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.message = message


class UpstreamError(GatewayError):
    def __init__(
        self, service: str, *, timed_out: bool = False, upstream_status: int | None = None,
        unavailable: bool = False,
    ) -> None:
        message = (
            f"Сервис {service} не ответил вовремя"
            if timed_out else f"Не удалось получить корректный ответ от сервиса {service}"
        )
        if unavailable:
            super().__init__(503, f"{service} Service unavailable")
        else:
            super().__init__(504 if timed_out else 502, message)
        self.upstream_status = upstream_status

    @property
    def rejected(self) -> bool:
        return self.upstream_status in (400, 404, 409, 422)


class ServiceUnavailable(UpstreamError):
    def __init__(self, service: str) -> None:
        super().__init__(service, unavailable=True)


class InvalidBooking(GatewayError):
    def __init__(self, field: str, error: str) -> None:
        super().__init__(400, "Ошибка валидации данных")
        self.field = field
        self.error = error
