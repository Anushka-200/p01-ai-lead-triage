"""The worker: takes one saved message all the way to Sheets/Slack, safely repeatable."""

import time
from collections.abc import Callable

import psycopg

from app.db import (
    Status,
    create_approval,
    get_message,
    insert_dlq,
    list_open_dlq,
    mark_replayed,
    save_card,
    set_status,
)
from app.delivery import card_of, deliver_slack_alert, deliver_to_sheet
from app.extractor import Extraction, extract_card
from app.ports import SheetsPort, SlackPort
from app.retry import GaveUp, call_with_retry
from app.schemas import Category

# Nothing more for the worker to do with a message in these states.
_STOP = {Status.DELIVERED, Status.REJECTED, Status.WAITING_APPROVAL, Status.FAILED}


def _fail(conn: psycopg.Connection, message_id: int, stage: str, err: GaveUp) -> Status:
    """Park the message on the DLQ shelf with the reason, and never lose it."""
    insert_dlq(conn, message_id, stage, str(err), err.attempts)
    set_status(conn, message_id, Status.FAILED)
    return Status.FAILED


def process_message(
    conn: psycopg.Connection,
    message_id: int,
    sheets: SheetsPort,
    slack: SlackPort,
    extract: Callable[[str], Extraction] = extract_card,
    sleep: Callable[[float], None] = time.sleep,
) -> Status:
    msg = get_message(conn, message_id)
    if msg.status in _STOP:
        return msg.status

    # 1. Extract (skipped if an earlier attempt already saved the card)
    if msg.card_json is None:
        try:
            extraction = call_with_retry(lambda: extract(msg.raw_text), sleep=sleep)
        except GaveUp as e:
            return _fail(conn, message_id, "extract", e)
        save_card(conn, message_id, extraction)
        msg = get_message(conn, message_id)

    # 2. Sensitive messages wait for a human. Nothing is written or sent yet.
    if card_of(msg).category is Category.REFUND_COMPLAINT:
        create_approval(conn, message_id)
        set_status(conn, message_id, Status.WAITING_APPROVAL)
        return Status.WAITING_APPROVAL

    # 3. Deliver. Each step checks its own "already done" flag, so a retry never repeats it.
    try:
        call_with_retry(lambda: deliver_to_sheet(conn, msg, sheets), sleep=sleep)
    except GaveUp as e:
        return _fail(conn, message_id, "sheets", e)
    try:
        call_with_retry(lambda: deliver_slack_alert(conn, msg, slack), sleep=sleep)
    except GaveUp as e:
        return _fail(conn, message_id, "slack", e)

    set_status(conn, message_id, Status.DELIVERED)
    return Status.DELIVERED


def replay(
    conn: psycopg.Connection,
    dlq_id: int,
    sheets: SheetsPort,
    slack: SlackPort,
    extract: Callable[[str], Extraction] = extract_card,
    sleep: Callable[[float], None] = time.sleep,
) -> Status:
    """Re-run a parked message from where it stopped. A new failure makes a new DLQ row."""
    row = conn.execute(
        "SELECT message_id FROM dlq WHERE id = %s AND replayed_at IS NULL", (dlq_id,)
    ).fetchone()
    if row is None:
        raise KeyError(f"no open DLQ item {dlq_id}")
    message_id = row[0]
    msg = get_message(conn, message_id)
    set_status(conn, message_id, Status.EXTRACTED if msg.card_json else Status.RECEIVED)
    result = process_message(conn, message_id, sheets, slack, extract, sleep)
    mark_replayed(conn, dlq_id)
    return result


def open_dlq_ids(conn: psycopg.Connection) -> list[int]:
    return [r[0] for r in list_open_dlq(conn)]


def stale_message_ids(conn: psycopg.Connection, older_than_s: int = 120) -> list[int]:
    """Messages saved but never finished (e.g. the server died mid-way). Worth re-running."""
    rows = conn.execute(
        "SELECT id FROM messages WHERE status IN ('received', 'extracted') "
        "AND received_at < now() - make_interval(secs => %s) ORDER BY id",
        (older_than_s,),
    ).fetchall()
    return [r[0] for r in rows]
