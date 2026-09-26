from collections.abc import Iterator
from contextlib import asynccontextmanager

import psycopg
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from pydantic import BaseModel, Field

from app.db import connect, init_db, register_message
from app.settings import settings
from app.signing import verify


class FormSubmission(BaseModel):
    email: str = Field(max_length=320)
    message: str = Field(min_length=1, max_length=20_000)
    name: str | None = Field(None, max_length=200)


@asynccontextmanager
async def lifespan(app: FastAPI):
    conn = connect()
    init_db(conn)
    conn.close()
    yield


app = FastAPI(title="P01 lead triage", lifespan=lifespan)


def get_conn() -> Iterator[psycopg.Connection]:
    conn = connect()
    try:
        yield conn
    finally:
        conn.close()


@app.post("/webhook", status_code=202)
async def webhook(
    request: Request,
    x_timestamp: str = Header(...),
    x_signature: str = Header(...),
    conn: psycopg.Connection = Depends(get_conn),
):
    body = await request.body()
    if len(body) > settings.webhook_max_body_bytes:
        raise HTTPException(413, "body too large")
    if not verify(
        settings.webhook_shared_secret, x_timestamp, body, x_signature, settings.webhook_max_age_s
    ):
        # One vague message on purpose: don't tell an attacker which check failed.
        raise HTTPException(401, "invalid signature")

    try:
        form = FormSubmission.model_validate_json(body)
    except ValueError as e:
        raise HTTPException(422, "invalid form data") from e

    result = register_message(conn, form.email, form.message, source="form")
    # Reply at once. Extraction, Sheets and Slack happen later, from the saved row.
    return {"status": "received", "message_id": result.message_id, "action": result.action.value}


@app.get("/health")
def health():
    return {"ok": True}
