import uuid
from datetime import datetime

from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, TIMESTAMP, ForeignKey, CheckConstraint, Index

from app.base import Base

class Reservation(Base):
    __tablename__ = "reservation"
    __table_args__ = (Index("ix_reservation_username_id", "username", "id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    reservation_uid: Mapped[uuid.UUID] = mapped_column(unique=True)
    username: Mapped[str] = mapped_column(String(80))
    payment_uid: Mapped[uuid.UUID]
    hotel_id: Mapped[int] = mapped_column(ForeignKey("hotels.id"))
    status: Mapped[str] = mapped_column(
        String(20),
        CheckConstraint("status in ('PAID', 'CANCELED')")
    )
    start_date: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    end_date: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))


class Hotel(Base):
    __tablename__ = "hotels"

    id: Mapped[int] = mapped_column(primary_key=True)
    hotel_uid: Mapped[uuid.UUID] = mapped_column(unique=True)
    name: Mapped[str] = mapped_column(String(255))
    country: Mapped[str] = mapped_column(String(80))
    city: Mapped[str] = mapped_column(String(80))
    address: Mapped[str] = mapped_column(String(255))
    stars: Mapped[int | None]
    price: Mapped[int]
