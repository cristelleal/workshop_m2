import asyncio
import logging
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from decimal import Decimal
from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from prometheus_client import Counter
from prometheus_fastapi_instrumentator import Instrumentator
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import DateTime, Numeric, String, create_engine, select, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("api")

def database_url() -> str:
    # Le compose du host fournit "postgresql://..." : SQLAlchemy choisirait alors psycopg2,
    # qui n'est pas installé. On force le driver psycopg 3.
    url = os.environ["DATABASE_URL"]
    for prefix in ("postgresql://", "postgres://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    return url


engine = create_engine(database_url(), pool_pre_ping=True)
DB_STARTUP_RETRIES = 30

TRANSACTIONS = Counter(
    "transactions_total",
    "Transactions traitées par l'API, par statut",
    ["status"],
)


class Base(DeclarativeBase):
    pass


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    currency: Mapped[str] = mapped_column(String(3))
    frequency: Mapped[str] = mapped_column(String(10))
    status: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class TransactionIn(BaseModel):
    amount: Decimal = Field(gt=0, le=10000, decimal_places=2)
    currency: Literal["EUR"] = "EUR"
    frequency: Literal["once", "monthly"] = "once"


class TransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    amount: Decimal
    currency: str
    frequency: str
    status: str
    created_at: datetime
    processed_at: datetime | None


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Pas de migrations Alembic pour l'instant : on crée la table si elle manque.
    # La base peut démarrer après l'API (depends_on sans healthcheck) : on réessaie.
    for attempt in range(1, DB_STARTUP_RETRIES + 1):
        try:
            Base.metadata.create_all(engine)
            break
        except OperationalError:
            if attempt == DB_STARTUP_RETRIES:
                raise
            logger.warning("base pas encore prete (essai %s/%s), nouvel essai dans 2s", attempt, DB_STARTUP_RETRIES)
            await asyncio.sleep(2)
    yield


app = FastAPI(title="Resilience API", lifespan=lifespan)

Instrumentator(excluded_handlers=["/metrics", "/healthz"]).instrument(app).expose(
    app, include_in_schema=False
)


@app.get("/healthz")
def healthz():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        logger.exception("healthcheck: base injoignable")
        return JSONResponse(status_code=503, content={"status": "error", "db": "unreachable"})
    return {"status": "ok", "db": "connected"}


@app.post("/transactions", response_model=TransactionOut, status_code=201)
def create_transaction(payload: TransactionIn):
    """Initie puis traite une transaction fictive (aucune donnée bancaire)."""
    now = datetime.now(timezone.utc)
    tx = Transaction(
        id=str(uuid.uuid4()),
        amount=payload.amount,
        currency=payload.currency,
        frequency=payload.frequency,
        status="pending",
        created_at=now,
    )
    with Session(engine) as session:
        session.add(tx)
        session.commit()
        logger.info("transaction initiee id=%s amount=%s %s", tx.id, tx.amount, tx.currency)

        tx.status = "completed"
        tx.processed_at = datetime.now(timezone.utc)
        session.commit()
        session.refresh(tx)

    TRANSACTIONS.labels(status=tx.status).inc()
    logger.info("transaction traitee id=%s status=%s", tx.id, tx.status)
    return tx


@app.get("/transactions", response_model=list[TransactionOut])
def list_transactions(limit: int = Query(default=20, ge=1, le=100)):
    with Session(engine) as session:
        rows = session.scalars(
            select(Transaction).order_by(Transaction.created_at.desc()).limit(limit)
        ).all()
    return rows


@app.get("/transactions/{tx_id}", response_model=TransactionOut)
def get_transaction(tx_id: str):
    with Session(engine) as session:
        tx = session.get(Transaction, tx_id)
    if tx is None:
        raise HTTPException(status_code=404, detail="transaction introuvable")
    return tx
