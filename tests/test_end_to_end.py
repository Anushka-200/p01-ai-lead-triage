"""Webhook -> saved -> worker -> Sheets/Slack, with fakes for Google, Slack and the AI."""

import json
import time

import pytest
from fastapi.testclient import TestClient

from app.api import app, get_conn, get_processor
from app.db import Status, get_message, register_message
from app.pipeline import process_message, stale_message_ids
from app.settings import settings
from app.signing import sign
from tests.fakes import FakeSheets, FakeSlack
from tests.test_pipeline import NO_WAIT, extraction

SECRET = "test-secret"


@pytest.fixture
def system(conn, monkeypatch):
    monkeypatch.setattr(settings, "webhook_shared_secret", SECRET)
    sheets, slack, calls = FakeSheets(), FakeSlack(), []
    kind = {"category": "new_lead", "priority": 5}

    def processor():
        def run(message_id):
            calls.append(message_id)
            process_message(
                conn, message_id, sheets, slack,
                lambda text: extraction(kind["priority"], kind["category"]), NO_WAIT,
            )  # fmt: skip

        return run

    app.dependency_overrides[get_conn] = lambda: conn
    app.dependency_overrides[get_processor] = processor
    yield TestClient(app), sheets, slack, calls, kind
    app.dependency_overrides.clear()


def send(client, email="raj@acme.com", message="We need a website by next month.", sig=None):
    body = json.dumps({"email": email, "message": message}).encode()
    ts = str(int(time.time()))
    return client.post(
        "/webhook",
        content=body,
        headers={"X-Timestamp": ts, "X-Signature": sig or sign(SECRET, ts, body)},
    )


def test_hot_lead_flows_from_form_to_sheet_and_slack(system, conn):
    client, sheets, slack, _calls, _ = system
    r = send(client)
    mid = r.json()["message_id"]
    assert r.status_code == 202
    assert get_message(conn, mid).status is Status.DELIVERED
    assert list(sheets.rows) == [mid] and slack.alerts == [mid]


def test_duplicate_submission_is_processed_only_once(system):
    client, sheets, slack, calls, _ = system
    send(client)
    second = send(client)
    assert second.json()["action"] == "skip"
    assert len(calls) == 1 and len(sheets.rows) == 1 and len(slack.alerts) == 1


def test_refund_message_stops_at_approval(system, conn):
    client, sheets, slack, _, kind = system
    kind["category"] = "refund_complaint"
    mid = send(client, message="I want my money back").json()["message_id"]
    assert get_message(conn, mid).status is Status.WAITING_APPROVAL
    assert sheets.rows == {} and slack.alerts == []


def test_forged_request_starts_no_processing(system):
    client, sheets, _slack, calls, _ = system
    assert send(client, sig="0" * 64).status_code == 401
    assert calls == [] and sheets.rows == {}


def test_worker_crash_does_not_break_the_reply_and_message_is_resumable(system, conn):
    client, *_ = system

    def exploding():
        def run(message_id):
            raise RuntimeError("bug")

        return run

    app.dependency_overrides[get_processor] = exploding
    with pytest.raises(RuntimeError):  # TestClient re-raises; a real server logs it
        send(client)
    mid = conn.execute("SELECT id FROM messages").fetchone()[0]
    assert get_message(conn, mid).status is Status.RECEIVED  # saved, waiting to be resumed


def test_stale_unfinished_messages_are_found_for_the_sweep(conn):
    old = register_message(conn, "a@x.com", "old", "form").message_id
    register_message(conn, "b@x.com", "fresh", "form")
    done = register_message(conn, "c@x.com", "done", "form").message_id
    conn.execute(
        "UPDATE messages SET received_at = now() - interval '10 minutes' WHERE id IN (%s, %s)",
        (old, done),
    )
    conn.execute("UPDATE messages SET status = 'delivered' WHERE id = %s", (done,))
    assert stale_message_ids(conn, older_than_s=120) == [old]
