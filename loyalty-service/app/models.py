from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.base import Base

class Loyalty(Base):
    __tablename__ = "loyalty"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True)
    reservation_count: Mapped[int] = mapped_column(server_default=text("0"))
    status: Mapped[str] = mapped_column(
        String(80),
        CheckConstraint("status in ('BRONZE', 'SILVER', 'GOLD')"),
        server_default="BRONZE"
    )
    discount: Mapped[int]


class LoyaltyReservation(Base):
    __tablename__ = "loyalty_reservation"

    reservation_uid: Mapped[UUID] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(80), ForeignKey("loyalty.username"))
    active: Mapped[bool]
