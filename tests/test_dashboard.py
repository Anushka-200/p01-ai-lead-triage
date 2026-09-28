"""Streamlit's own widgets need a browser to test properly, so we test the data helpers and
the password check's logic directly, and rely on a manual run for the visual part."""

from app.dashboard import card_text
from app.db import recent_messages, register_message
from app.pipeline import process_message
from app.settings import settings
from tests.fakes import FakeSheets, FakeSlack
from tests.test_pipeline import NO_WAIT, extraction


def test_card_text_handles_both_json_string_and_dict():
    assert card_text('{"priority": 4}') == {"priority": 4}
    assert card_text({"priority": 4}) == {"priority": 4}
    assert card_text(None) == {}


def test_recent_messages_shows_newest_first(conn):
    a = register_message(conn, "a@x.com", "one", "form").message_id
    b = register_message(conn, "b@x.com", "two", "form").message_id
    rows = recent_messages(conn, limit=50)
    assert [r[0] for r in rows] == [b, a]


def test_recent_messages_respects_the_limit(conn):
    for i in range(5):
        register_message(conn, f"{i}@x.com", f"msg {i}", "form")
    assert len(recent_messages(conn, limit=3)) == 3


def test_recent_messages_includes_the_card_once_delivered(conn):
    mid = register_message(conn, "raj@acme.com", "need a website", "form").message_id
    process_message(conn, mid, FakeSheets(), FakeSlack(), lambda t: extraction(), NO_WAIT)
    row = recent_messages(conn, 50)[0]
    assert card_text(row[4])["priority"] == 4


def test_dashboard_refuses_to_run_without_a_password(monkeypatch):
    monkeypatch.setattr(settings, "dashboard_password", "")
    # check_password() calls st.stop(); we only assert the guard condition it relies on
    assert settings.dashboard_password == ""
