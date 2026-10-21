from prometheus_client import Counter, Histogram

# Label "amount" : "5", "10", "25", "50" ou "libre" -> cardinalité bornée
DONATIONS_TOTAL = Counter(
    "donations_total",
    "Nombre de tentatives de don",
    ["status", "amount"],
)

DONATIONS_AMOUNT_EUROS = Counter(
    "donations_amount_euros_total",
    "Montant cumulé des dons réussis, en euros",
    ["amount"],
)

PAYMENT_DURATION = Histogram(
    "payment_processing_seconds",
    "Durée de traitement du paiement simulé",
)