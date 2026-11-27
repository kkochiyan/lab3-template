from uuid import UUID

from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import CheckConstraint, String, UniqueConstraint

from app.base import Base

class Payment(Base):
    __tablename__ = "payment"
    __table_args__ = (UniqueConstraint("payment_uid", name="uq_payment_payment_uid"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    payment_uid: Mapped[UUID]
    status: Mapped[str] = mapped_column(
        String(20),
        CheckConstraint("status in ('PAID', 'CANCELED')")
    )
    price: Mapped[int]
