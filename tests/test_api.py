import json
import time

import pytest
from fastapi.testclient import TestClient

from app.api import app, get_conn
from app.settings import settings
from app.signing import sign

SECRET = "test-secret"
BODY = json.dumps({"email": "raj@acme.com", "message": "We need a website by next month."}).encode()


@pytest.fixture
def client(conn, monkeypatch):
    monkeypatch.setattr(settings, "webhook_shared_secret", SECRET)
    app.dependency_overrides[get_conn] = lambda: conn
    yield TestClient(app)
    app.dependency_overrides.clear()


def post(client, body=BODY, ts=None, sig=None):
    ts = ts or str(int(time.time()))
    sig = sig or sign(SECRET, ts, body)
    return client.post("/webhook", content=body, headers={"X-Timestamp": ts, "X-Signature": sig})


def rows(conn) -> int:
    return conn.execute("SELECT count(*) FROM messages").fetchone()[0]


def test_genuine_message_is_saved_and_gets_202(client, conn):
    r = post(client)
    assert r.status_code == 202
    assert r.json()["action"] == "new"
    assert rows(conn) == 1


def test_same_message_twice_is_one_row(client, conn):
    post(client)
    conn.execute("UPDATE messages SET status = 'delivered'")
    r = post(client)
    assert r.status_code == 202
    assert r.json()["action"] == "skip"
    assert rows(conn) == 1


def test_forged_signature_is_rejected_and_nothing_saved(client, conn):
    r = post(client, sig="0" * 64)
    assert r.status_code == 401
    assert rows(conn) == 0


def test_stale_timestamp_is_rejected(client, conn):
    old = str(int(time.time()) - 3600)
    assert post(client, ts=old).status_code == 401
    assert rows(conn) == 0


def test_tampered_body_is_rejected(client, conn):
    ts = str(int(time.time()))
    sig = sign(SECRET, ts, BODY)
    assert post(client, body=BODY.replace(b"website", b"villa"), ts=ts, sig=sig).status_code == 401
    assert rows(conn) == 0


def test_missing_headers_are_rejected(client):
    assert client.post("/webhook", content=BODY).status_code == 422


def test_signed_but_invalid_form_gets_422(client, conn):
    body = b'{"email": "a@x.com"}'  # no message
    assert post(client, body=body).status_code == 422
    assert rows(conn) == 0


def test_oversized_body_is_rejected(client, monkeypatch):
    monkeypatch.setattr(settings, "webhook_max_body_bytes", 10)
    assert post(client).status_code == 413


def test_no_secret_configured_rejects_everything(client, monkeypatch):
    monkeypatch.setattr(settings, "webhook_shared_secret", "")
    assert post(client).status_code == 401
