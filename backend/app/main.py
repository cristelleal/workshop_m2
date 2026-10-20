import os
from fastapi import FastAPI
from sqlalchemy import create_engine, text

app = FastAPI(title="Mon API")
engine = create_engine(os.environ["DATABASE_URL"], pool_pre_ping=True)

@app.get("/health")
def health():
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return {"status": "ok", "db": "connected"}