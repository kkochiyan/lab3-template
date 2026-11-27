from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[1] / ".env",
        env_file_encoding="utf-8",
    )

    reservation_service_host: str = "localhost"
    reservation_service_port: int = 8070
    payment_service_host: str = "localhost"
    payment_service_port: int = 8060
    loyalty_service_host: str = "localhost"
    loyalty_service_port: int = 8050

    @property
    def reservation_service_base_url(self) -> str:
        return f"http://{self.reservation_service_host}:{self.reservation_service_port}"

    @property
    def payment_service_base_url(self) -> str:
        return f"http://{self.payment_service_host}:{self.payment_service_port}"

    @property
    def loyalty_service_base_url(self) -> str:
        return f"http://{self.loyalty_service_host}:{self.loyalty_service_port}"

settings = Settings()
