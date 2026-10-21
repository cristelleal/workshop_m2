from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class DonationStatus(StrEnum):
    pending = "pending"
    succeeded = "succeeded"
    failed = "failed"


class DonationFrequency(StrEnum):
    once = "once"
    monthly = "monthly"


class Donation(Base):
    __tablename__ = "donations"

    # UUID plutôt qu'un entier : impossible de deviner les dons des autres
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    amount_cents: Mapped[int]
    currency: Mapped[str] = mapped_column(String(3), default="EUR")
    frequency: Mapped[DonationFrequency] = mapped_column(
        Enum(DonationFrequency, name="donation_frequency"), default=DonationFrequency.once
    )
    is_custom: Mapped[bool]
    status: Mapped[DonationStatus] = mapped_column(
        Enum(DonationStatus, name="donation_status"), default=DonationStatus.pending
    )
    card_last4: Mapped[str | None] = mapped_column(String(4))
    failure_reason: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))