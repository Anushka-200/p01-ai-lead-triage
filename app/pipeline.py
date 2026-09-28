"""The worker: takes one saved message all the way to Sheets/Slack, safely repeatable."""

import time
from collections.abc import Callable

import psycopg

from app.db import (
    Status,
    claim_message,
    create_approval,
    decide_approval,
    get_message,
    insert_dlq,
    list_open_dlq,
    mark_replayed,
    release_message,
    save_card,
    set_status,
)
from app.delivery import card_of, deliver_slack_alert, deliver_to_sheet
from app.extractor import Extraction, extract_card
from app.ports import SheetsPort, SlackPort
from app.retry import GaveUp, call_with_retry
from app.schemas import Category, LeadCard

# Nothing more for the worker to do with a message in these states.
_STOP = {Status.DELIVERED, Status.REJECTED, Status.WAITING_APPROVAL, Status.FAILED}


def _fail(conn: psycopg.Connection, message_id: int, stage: str, err: GaveUp) -> Status:
    """Park the message on the DLQ shelf with the reason, and never lose it."""
    insert_dlq(conn, message_id, stage, str(err), err.attempts)
    set_status(conn, message_id, Status.FAILED)
    return Status.FAILED


def _valid_email(value: str | None) -> bool:
    return bool(value) and "@" in value and " " not in value


def fill_from_form(card: LeadCard, email: str | None, name: str | None) -> LeadCard:
    """The form told us who wrote in. Use it when the message text didn't say."""
    update = {}
    if card.email is None and _valid_email(email):
        update["email"] = email
    if card.name is None and name and name.strip():
        update["name"] = name.strip()[:200]
    return card.model_copy(update=update) if update else card


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
    if not claim_message(conn, message_id):  # another worker is on it right now
        return msg.status
    try:
        return _run(conn, msg, sheets, slack, extract, sleep)
    finally:
        release_message(conn, message_id)  # a replay must not wait for the lease to expire


def _run(
    conn: psycopg.Connection,
    msg,
    sheets: SheetsPort,
    slack: SlackPort,
    extract: Callable[[str], Extraction],
    sleep: Callable[[float], None],
) -> Status:
    message_id = msg.id

    # 1. Extract (skipped if an earlier attempt already saved the card)
    if msg.card_json is None:
        try:
            extraction = call_with_retry(lambda: extract(msg.raw_text), sleep=sleep)
        except GaveUp as e:
            return _fail(conn, message_id, "extract", e)
        extraction.card = fill_from_form(extraction.card, msg.sender_email, msg.sender_name)
        save_card(conn, message_id, extraction)
        msg = get_message(conn, message_id)

    # 2. Sensitive messages wait for a human. Nothing is written or sent yet.
    if card_of(msg).category is Category.REFUND_COMPLAINT:
        create_approval(conn, message_id)
        set_status(conn, message_id, Status.WAITING_APPROVAL)
        return Status.WAITING_APPROVAL

    # 3. Deliver. Each step checks its own "already done" flag, so a retry never repeats it.
    return _deliver(conn, msg, sheets, slack, sleep)


def _deliver(conn, msg, sheets: SheetsPort, slack: SlackPort, sleep) -> Status:
    message_id = msg.id
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


def decide(
    conn: psycopg.Connection,
    approval_id: int,
    approved: bool,
    sheets: SheetsPort,
    slack: SlackPort,
    sleep: Callable[[float], None] = time.sleep,
) -> Status | None:
    """Priya clicked Approve or Reject on a held message. Returns the new status, or None if
    this approval was already decided (e.g. a double click)."""
    message_id = decide_approval(conn, approval_id, approved)
    if message_id is None:
        return None
    if not approved:
        set_status(conn, message_id, Status.REJECTED)
        return Status.REJECTED
    # Approved: run the normal delivery steps (Sheets, then Slack if hot). The category check
    # in process_message would hold it again, so we call _deliver directly instead.
    set_status(conn, message_id, Status.EXTRACTED)
    if not claim_message(conn, message_id):
        return get_message(conn, message_id).status
    try:
        return _deliver(conn, get_message(conn, message_id), sheets, slack, sleep)
    finally:
        release_message(conn, message_id)
