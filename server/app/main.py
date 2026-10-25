"""API for the New Vegas Dialogue Explorer.

Card 1 only needs a health route. Search and NPC routes come in card 6.
"""

import os

import psycopg
from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI(
    title="New Vegas Dialogue Explorer API",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)


def database_ok() -> bool:
    """Return True if Postgres answers a trivial query within 2 seconds."""
    url = os.environ.get("DATABASE_URL")
    if not url:
        return False
    try:
        with psycopg.connect(url, connect_timeout=2) as conn:
            conn.execute("SELECT 1")
        return True
    except psycopg.Error:
        return False


@app.get("/api/health")
def health():
    """Report whether the API and the database are up.

    Returns 200 when both are up and 503 when the database is down,
    so the UI can tell the two apart.
    """
    if database_ok():
        return {"api": "ok", "db": "ok"}
    return JSONResponse(status_code=503, content={"api": "ok", "db": "down"})
