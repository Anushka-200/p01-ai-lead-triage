"""Integration tests against a real Postgres (database p01_test). Skipped if it isn't running."""

import psycopg
import pytest

from app.db import Action, Status, connect, init_db, register_message

TEST_URL = "postgresql://p01:p01@localhost:5433/p01_test"


@pytest.fixture
def conn():
    try:
        c = connect(TEST_URL)
    except psycopg.OperationalError:
        pytest.skip("Postgres test database not available (run: docker compose up -d)")
    init_db(c)
    c.execute("TRUNCATE dlq, approvals, messages RESTART IDENTITY CASCADE")
    yield c
    c.close()


def count(conn) -> int:
    return conn.execute("SELECT count(*) FROM messages").fetchone()[0]


def test_new_message_is_saved_as_received(conn):
    r = register_message(conn, "raj@acme.com", "need a website", "form")
    assert r.action is Action.NEW
    status = conn.execute("SELECT status FROM messages WHERE id = %s", (r.message_id,)).fetchone()[
        0
    ]
    assert status == Status.RECEIVED.value


def test_same_message_twice_creates_one_row(conn):
    first = register_message(conn, "raj@acme.com", "need a website", "form")
    conn.execute("UPDATE messages SET status = 'delivered' WHERE id = %s", (first.message_id,))
    second = register_message(conn, "Raj@Acme.com ", "Need a  website", "form")
    assert second.action is Action.SKIP
    assert second.message_id == first.message_id
    assert count(conn) == 1


def test_crash_midway_is_resumed_not_swallowed(conn):
    first = register_message(conn, "raj@acme.com", "need a website", "form")
    # simulate: the app died right after saving, status is still 'received'
    again = register_message(conn, "raj@acme.com", "need a website", "form")
    assert again.action is Action.RESUME
    assert again.message_id == first.message_id
    assert count(conn) == 1


@pytest.mark.parametrize("status", ["delivered", "waiting_approval", "rejected", "failed"])
def test_handled_statuses_are_skipped(conn, status):
    first = register_message(conn, "a@x.com", "hello", "form")
    conn.execute("UPDATE messages SET status = %s WHERE id = %s", (status, first.message_id))
    assert register_message(conn, "a@x.com", "hello", "form").action is Action.SKIP


def test_extracted_status_is_resumed(conn):
    first = register_message(conn, "a@x.com", "hello", "form")
    conn.execute("UPDATE messages SET status = 'extracted' WHERE id = %s", (first.message_id,))
    assert register_message(conn, "a@x.com", "hello", "form").action is Action.RESUME


def test_database_rejects_unknown_status(conn):
    first = register_message(conn, "a@x.com", "hello", "form")
    with pytest.raises(psycopg.errors.CheckViolation):
        conn.execute("UPDATE messages SET status = 'oops' WHERE id = %s", (first.message_id,))


def test_database_rejects_duplicate_fingerprint_directly(conn):
    register_message(conn, "a@x.com", "hello", "form")
    fp = conn.execute("SELECT fingerprint FROM messages").fetchone()[0]
    with pytest.raises(psycopg.errors.UniqueViolation):
        conn.execute(
            "INSERT INTO messages (fingerprint, source, raw_text) VALUES (%s,'form','x')", (fp,)
        )
