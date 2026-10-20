from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy import text

from app.core.config import settings
from app.core.logging import setup_logging
from app.db import engine
from app.routes import auth, donations

setup_logging(settings.log_level)

app = FastAPI(title="API Dons")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(donations.router)

Instrumentator(excluded_handlers=["/metrics", "/healthz"]).instrument(app).expose(
    app, include_in_schema=False
)


@app.get("/healthz", include_in_schema=False)
def healthz():
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return {"status": "ok"}