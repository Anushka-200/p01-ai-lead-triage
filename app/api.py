import logging
from collections.abc import Callable, Iterator
from contextlib import asynccontextmanager
from functools import lru_cache

import psycopg
from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException, Request
from pydantic import BaseModel, Field

from app.db import Action, connect, init_db, register_message
from app.pipeline import process_message
from app.settings import settings
from app.sheets import GoogleSheets
from app.signing import verify
from app.slack import SlackNotifier

log = logging.getLogger("p01")


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


@lru_cache
def _outputs() -> tuple[GoogleSheets, SlackNotifier]:
    return GoogleSheets(), SlackNotifier()  # created once, on first use


def get_processor() -> Callable[[int], None]:
    """The background job for one saved message. Tests replace this with a fake-backed one."""

    def run(message_id: int) -> None:
        conn = connect()
        try:
            sheets, slack = _outputs()
            process_message(conn, message_id, sheets, slack)
        except Exception:
            # Unexpected bug or setup problem. The row stays 'received', so a resend resumes it.
            log.exception("processing failed for message %s", message_id)
        finally:
            conn.close()

    return run


@app.post("/webhook", status_code=202)
async def webhook(
    request: Request,
    background: BackgroundTasks,
    process: Callable[[int], None] = Depends(get_processor),
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

    result = register_message(conn, form.email, form.message, source="form", name=form.name)
    if result.action in (Action.NEW, Action.RESUME):
        # Runs after the 202 reply is sent: extraction, Sheets and Slack, from the saved row.
        background.add_task(process, result.message_id)
    return {"status": "received", "message_id": result.message_id, "action": result.action.value}


@app.get("/health")
def health():
    return {"ok": True}
