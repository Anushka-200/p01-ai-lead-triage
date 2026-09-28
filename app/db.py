from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

import psycopg

from app.dedupe import fingerprint
from app.settings import settings

if TYPE_CHECKING:
    from app.extractor import Extraction


class Status(str, Enum):
    RECEIVED = "received"  # saved, nothing else done
    EXTRACTED = "extracted"  # AI card created and validated
    WAITING_APPROVAL = "waiting_approval"  # held for a human
    DELIVERED = "delivered"  # in the Sheet (and Slack if hot). Done.
    REJECTED = "rejected"  # human said no. Done.
    FAILED = "failed"  # gave up after retries; on the DLQ


# A repeat of a message in one of these states is skipped; anything else is resumed.
HANDLED = {Status.DELIVERED, Status.WAITING_APPROVAL, Status.REJECTED, Status.FAILED}


class Action(str, Enum):
    NEW = "new"
    SKIP = "skip"
    RESUME = "resume"


@dataclass
class Registered:
    message_id: int
    action: Action


def _in_list(values) -> str:
    return ", ".join(f"'{v.value}'" for v in values)


SCHEMA = f"""
CREATE TABLE IF NOT EXISTS messages (
    id             BIGSERIAL PRIMARY KEY,
    fingerprint    TEXT NOT NULL UNIQUE,
    source         TEXT NOT NULL CHECK (source IN ('form', 'gmail')),
    received_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    raw_text       TEXT NOT NULL,
    card_json      JSONB,
    status         TEXT NOT NULL DEFAULT 'received' CHECK (status IN ({_in_list(Status)})),
    sheet_written  BOOLEAN NOT NULL DEFAULT false,
    slack_sent     BOOLEAN NOT NULL DEFAULT false,
    model_used     TEXT,
    tokens_in      INTEGER,
    tokens_out     INTEGER,
    cost_usd       NUMERIC(10, 6),
    prompt_version TEXT
);

CREATE TABLE IF NOT EXISTS approvals (
    id         BIGSERIAL PRIMARY KEY,
    message_id BIGINT NOT NULL REFERENCES messages(id),
    status     TEXT NOT NULL DEFAULT 'pending'
               CHECK (status IN ('pending', 'approved', 'rejected')),
    decided_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS dlq (
    id          BIGSERIAL PRIMARY KEY,
    message_id  BIGINT NOT NULL REFERENCES messages(id),
    stage       TEXT NOT NULL CHECK (stage IN ('extract', 'sheets', 'slack')),
    error       TEXT NOT NULL,
    attempts    INTEGER NOT NULL DEFAULT 1,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    replayed_at TIMESTAMPTZ
);
"""


MIGRATIONS = """
ALTER TABLE messages ADD COLUMN IF NOT EXISTS sender_email TEXT;
ALTER TABLE messages ADD COLUMN IF NOT EXISTS sender_name TEXT;
ALTER TABLE messages ADD COLUMN IF NOT EXISTS locked_until TIMESTAMPTZ;
"""


def connect(url: str | None = None) -> psycopg.Connection:
    return psycopg.connect(url or settings.database_url, autocommit=True)


def init_db(conn: psycopg.Connection) -> None:
    conn.execute(SCHEMA)
    conn.execute(MIGRATIONS)


def register_message(
    conn: psycopg.Connection, sender: str, text: str, source: str, name: str | None = None
) -> Registered:
    """Save a new message, or decide what to do about a repeat. The database is the judge."""
    fp = fingerprint(sender, text)
    row = conn.execute(
        "INSERT INTO messages (fingerprint, source, raw_text, sender_email, sender_name) "
        "VALUES (%s, %s, %s, %s, %s) ON CONFLICT (fingerprint) DO NOTHING RETURNING id",
        (fp, source, text, sender, name),
    ).fetchone()
    if row:
        return Registered(row[0], Action.NEW)

    # Already there: was the earlier attempt finished, or did it die halfway?
    message_id, status = conn.execute(
        "SELECT id, status FROM messages WHERE fingerprint = %s", (fp,)
    ).fetchone()
    action = Action.SKIP if Status(status) in HANDLED else Action.RESUME
    return Registered(message_id, action)


@dataclass
class Message:
    id: int
    source: str
    received_at: datetime
    raw_text: str
    status: Status
    card_json: dict | None
    sheet_written: bool
    slack_sent: bool
    sender_email: str | None
    sender_name: str | None


def get_message(conn: psycopg.Connection, message_id: int) -> Message:
    row = conn.execute(
        "SELECT id, source, received_at, raw_text, status, card_json, sheet_written, slack_sent, "
        "sender_email, sender_name "
        "FROM messages WHERE id = %s",
        (message_id,),
    ).fetchone()
    if row is None:
        raise KeyError(f"message {message_id} not found")
    return Message(
        row[0], row[1], row[2], row[3], Status(row[4]), row[5], row[6], row[7], row[8], row[9]
    )


def save_card(conn: psycopg.Connection, message_id: int, extraction: "Extraction") -> None:
    """Store the validated card and the AI usage numbers, and move status to 'extracted'."""
    conn.execute(
        "UPDATE messages SET card_json = %s, status = 'extracted', model_used = %s, "
        "tokens_in = %s, tokens_out = %s, cost_usd = %s, prompt_version = %s WHERE id = %s",
        (
            extraction.card.model_dump_json(),
            extraction.model,
            extraction.tokens_in,
            extraction.tokens_out,
            extraction.cost_usd,
            extraction.prompt_version,
            message_id,
        ),
    )


def mark_sheet_written(conn: psycopg.Connection, message_id: int) -> None:
    conn.execute("UPDATE messages SET sheet_written = true WHERE id = %s", (message_id,))


def mark_slack_sent(conn: psycopg.Connection, message_id: int) -> None:
    conn.execute("UPDATE messages SET slack_sent = true WHERE id = %s", (message_id,))


def set_status(conn: psycopg.Connection, message_id: int, status: Status) -> None:
    conn.execute("UPDATE messages SET status = %s WHERE id = %s", (status.value, message_id))


def create_approval(conn: psycopg.Connection, message_id: int) -> None:
    conn.execute("INSERT INTO approvals (message_id) VALUES (%s)", (message_id,))


def list_pending_approvals(conn: psycopg.Connection) -> list[tuple]:
    """Held messages waiting on a human: (approval_id, message_id, raw_text, card_json, received_at)."""
    return conn.execute(
        "SELECT a.id, m.id, m.raw_text, m.card_json, m.received_at FROM approvals a "
        "JOIN messages m ON m.id = a.message_id WHERE a.status = 'pending' ORDER BY a.id"
    ).fetchall()


def decide_approval(conn: psycopg.Connection, approval_id: int, approved: bool) -> int | None:
    """Record the human's decision. Returns the message id, or None if already decided."""
    status = "approved" if approved else "rejected"
    row = conn.execute(
        "UPDATE approvals SET status = %s, decided_at = now() "
        "WHERE id = %s AND status = 'pending' RETURNING message_id",
        (status, approval_id),
    ).fetchone()
    return row[0] if row else None


def insert_dlq(
    conn: psycopg.Connection, message_id: int, stage: str, error: str, attempts: int
) -> None:
    conn.execute(
        "INSERT INTO dlq (message_id, stage, error, attempts) VALUES (%s, %s, %s, %s)",
        (message_id, stage, error[:1000], attempts),
    )


def list_open_dlq(conn: psycopg.Connection) -> list[tuple]:
    """Items still on the shelf: (id, message_id, stage, error, attempts, created_at)."""
    return conn.execute(
        "SELECT id, message_id, stage, error, attempts, created_at FROM dlq "
        "WHERE replayed_at IS NULL ORDER BY id"
    ).fetchall()


def mark_replayed(conn: psycopg.Connection, dlq_id: int) -> None:
    conn.execute("UPDATE dlq SET replayed_at = now() WHERE id = %s", (dlq_id,))


def claim_message(conn: psycopg.Connection, message_id: int, lease_s: int = 120) -> bool:
    """Try to mark the message 'mine for the next lease_s seconds'. One statement, so the
    database lets only one caller win. Returns False if someone else holds an unexpired claim."""
    row = conn.execute(
        "UPDATE messages SET locked_until = now() + make_interval(secs => %s) "
        "WHERE id = %s AND status IN ('received', 'extracted') "
        "AND (locked_until IS NULL OR locked_until < now()) RETURNING id",
        (lease_s, message_id),
    ).fetchone()
    return row is not None


def release_message(conn: psycopg.Connection, message_id: int) -> None:
    conn.execute("UPDATE messages SET locked_until = NULL WHERE id = %s", (message_id,))
