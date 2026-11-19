import os
import psycopg
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

DATABASE_URL = os.environ["DATABASE_URL"]
app = FastAPI()


class ItemIn(BaseModel):
    name: str


def db():
    conn = psycopg.connect(DATABASE_URL, connect_timeout=3)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS items "
        "(id SERIAL PRIMARY KEY, name TEXT NOT NULL)"
    )
    return conn


@app.exception_handler(psycopg.OperationalError)
async def db_unavailable(request: Request, exc: Exception):
    return JSONResponse(status_code=503, content={"detail": "database unavailable"})


@app.get("/health")
def health():
    with db() as conn:
        conn.execute("SELECT 1")
    return {"status": "ok"}


@app.post("/items", status_code=201)
def create_item(item: ItemIn):
    with db() as conn:
        row = conn.execute(
            "INSERT INTO items (name) VALUES (%s) RETURNING id, name", (item.name,)
        ).fetchone()
    return {"id": row[0], "name": row[1]}


@app.get("/items")
def list_items():
    with db() as conn:
        rows = conn.execute("SELECT id, name FROM items ORDER BY id").fetchall()
    return [{"id": r[0], "name": r[1]} for r in rows]
