import random
import time
from dataclasses import dataclass


@dataclass(frozen=True)
class PaymentResult:
    success: bool
    failure_reason: str | None = None


# Cartes de test, sur le modèle de celles de Stripe
TEST_CARDS: dict[str, str | None] = {
    "4242424242424242": None,                  # paiement accepté
    "4000000000000002": "card_declined",
    "4000000000009995": "insufficient_funds",
}


def process_payment(card_number: str, amount_cents: int) -> PaymentResult:
    """Simule un prestataire de paiement. Aucun appel externe.

    Pour brancher un vrai prestataire plus tard, il suffit de remplacer
    cette fonction en gardant la même signature et le même retour.
    """
    time.sleep(random.uniform(0.1, 0.6))  # latence réaliste, utile dans Grafana

    if card_number not in TEST_CARDS:
        return PaymentResult(success=False, failure_reason="unknown_test_card")

    reason = TEST_CARDS[card_number]
    return PaymentResult(success=reason is None, failure_reason=reason)