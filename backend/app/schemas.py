from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models import DonationStatus

PRESET_AMOUNTS_CENTS = (500, 1000, 2500, 5000)
MIN_AMOUNT_CENTS = 100          # 1 €
MAX_AMOUNT_CENTS = 1_000_000    # 10 000 €


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: EmailStr


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class DonationPresets(BaseModel):
    currency: str = "EUR"
    presets_cents: list[int]
    min_cents: int
    max_cents: int


class DonationCreate(BaseModel):
    amount_cents: int = Field(ge=MIN_AMOUNT_CENTS, le=MAX_AMOUNT_CENTS)
    card_number: str = Field(
        pattern=r"^\d{16}$",
        description="Numéro de carte de TEST uniquement (16 chiffres, sans espaces)",
    )


class DonationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    amount_cents: int
    currency: str
    is_custom: bool
    status: DonationStatus
    card_last4: str | None
    failure_reason: str | None
    created_at: datetime