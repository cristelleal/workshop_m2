import logging
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.core.metrics import DONATIONS_AMOUNT_EUROS, DONATIONS_TOTAL, PAYMENT_DURATION
from app.deps import CurrentUser, DbSession
from app.models import Donation, DonationStatus
from app.schemas import (
    MAX_AMOUNT_CENTS,
    MIN_AMOUNT_CENTS,
    PRESET_AMOUNTS_CENTS,
    DonationCreate,
    DonationOut,
    DonationPresets,
)
from app.service.payment import process_payment

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/donations", tags=["donations"])


@router.get("/presets", response_model=DonationPresets)
def get_presets():
    """Public : permet au front d'afficher les boutons 5/10/25/50 € et les bornes du montant libre."""
    return DonationPresets(
        presets_cents=list(PRESET_AMOUNTS_CENTS),
        min_cents=MIN_AMOUNT_CENTS,
        max_cents=MAX_AMOUNT_CENTS,
    )


@router.post("", response_model=DonationOut, status_code=status.HTTP_201_CREATED)
def create_donation(payload: DonationCreate, user: CurrentUser, db: DbSession):
    is_custom = payload.amount_cents not in PRESET_AMOUNTS_CENTS
    donation = Donation(
        user_id=user.id,
        amount_cents=payload.amount_cents,
        frequency=payload.frequency,
        is_custom=is_custom,
        card_last4=payload.card_number[-4:],
    )
    # On enregistre le don en "pending" AVANT le paiement : traçabilité si ça plante
    db.add(donation)
    db.commit()

    with PAYMENT_DURATION.time():
        result = process_payment(payload.card_number, payload.amount_cents)

    donation.status = DonationStatus.succeeded if result.success else DonationStatus.failed
    donation.failure_reason = result.failure_reason
    donation.processed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(donation)

    amount_label = "libre" if is_custom else str(payload.amount_cents // 100)
    DONATIONS_TOTAL.labels(status=donation.status.value, amount=amount_label).inc()
    if result.success:
        DONATIONS_AMOUNT_EUROS.labels(amount=amount_label).inc(payload.amount_cents / 100)

    logger.info(
        "donation_processed",
        extra={
            "donation_id": str(donation.id),
            "user_id": user.id,
            "amount_cents": donation.amount_cents,
            "status": donation.status.value,
            "failure_reason": donation.failure_reason,
        },
    )
    return donation


@router.get("/me", response_model=list[DonationOut])
def list_my_donations(
    user: CurrentUser,
    db: DbSession,
    limit: int = Query(default=20, ge=1, le=100),
):
    stmt = (
        select(Donation)
        .where(Donation.user_id == user.id)
        .order_by(Donation.created_at.desc())
        .limit(limit)
    )
    return db.scalars(stmt).all()


@router.get("/all", response_model=list[DonationOut])
def list_all_donations(
    user: CurrentUser,
    db: DbSession,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
):
    """Récupère TOUS les dons, tous utilisateurs confondus (pour l'export data/BI).

    ⚠️ Accessible à tout utilisateur authentifié : expose les dons de tout le monde.
    """
    stmt = (
        select(Donation)
        .order_by(Donation.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return db.scalars(stmt).all()


@router.get("/{donation_id}", response_model=DonationOut)
def get_donation(donation_id: UUID, user: CurrentUser, db: DbSession):
    donation = db.get(Donation, donation_id)
    # 404 aussi si le don appartient à quelqu'un d'autre : on ne révèle pas qu'il existe
    if donation is None or donation.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Don introuvable")
    return donation