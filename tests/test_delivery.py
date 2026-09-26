import json

import pytest

from app.db import Status, get_message, register_message, save_card
from app.delivery import deliver_slack_alert, deliver_to_sheet
from app.extractor import Extraction
from app.schemas import LeadCard
from tests.conftest import GOOD_CARD
from tests.fakes import FakeSheets, FakeSlack


def make_extraction(priority: int = 4) -> Extraction:
    card = LeadCard.model_validate_json(GOOD_CARD.replace('"priority":4', f'"priority":{priority}'))
    return Extraction(card, "anthropic/haiku", "v1", 1, 1374, 203, 0.0024)


@pytest.fixture
def saved(conn):
    """A message that already has its card saved (status 'extracted')."""

    def make(priority: int = 4):
        r = register_message(conn, "raj@acme.com", f"need a website p{priority}", "form")
        save_card(conn, r.message_id, make_extraction(priority))
        return r.message_id

    return make


def test_save_card_stores_card_usage_and_status(conn, saved):
    msg = get_message(conn, saved())
    assert msg.status is Status.EXTRACTED
    assert msg.card_json["priority"] == 4
    row = conn.execute(
        "SELECT model_used, tokens_in, tokens_out, cost_usd, prompt_version FROM messages"
    ).fetchone()
    assert row[0] == "anthropic/haiku" and (row[1], row[2]) == (1374, 203)
    assert float(row[3]) == pytest.approx(0.0024) and row[4] == "v1"


def test_get_message_unknown_id_raises(conn):
    with pytest.raises(KeyError):
        get_message(conn, 999)


def test_sheet_row_written_once_even_if_delivery_runs_twice(conn, saved):
    sheets, mid = FakeSheets(), saved()
    deliver_to_sheet(conn, get_message(conn, mid), sheets)
    deliver_to_sheet(conn, get_message(conn, mid), sheets)
    assert list(sheets.rows) == [mid]
    assert sheets.calls == 1  # second run saw sheet_written=true and did nothing
    assert get_message(conn, mid).sheet_written


def test_failed_sheet_write_is_not_marked_written(conn, saved):
    sheets, mid = FakeSheets(fail_times=1), saved()
    with pytest.raises(ConnectionError):
        deliver_to_sheet(conn, get_message(conn, mid), sheets)
    assert not get_message(conn, mid).sheet_written
    deliver_to_sheet(conn, get_message(conn, mid), sheets)  # retry succeeds
    assert list(sheets.rows) == [mid]


def test_lost_reply_then_retry_gives_one_row(conn, saved):
    """Row was written but the app never heard back. The retry must not add a second row."""
    sheets, mid = FakeSheets(fail_times=1, fail_after_write=True), saved()
    with pytest.raises(TimeoutError):
        deliver_to_sheet(conn, get_message(conn, mid), sheets)
    deliver_to_sheet(conn, get_message(conn, mid), sheets)
    assert list(sheets.rows) == [mid]


def test_hot_lead_sends_one_alert_even_if_run_twice(conn, saved):
    slack, mid = FakeSlack(), saved(priority=5)
    deliver_slack_alert(conn, get_message(conn, mid), slack)
    deliver_slack_alert(conn, get_message(conn, mid), slack)
    assert slack.alerts == [mid]
    assert get_message(conn, mid).slack_sent


@pytest.mark.parametrize("priority", [1, 2, 3])
def test_low_priority_sends_no_alert(conn, saved, priority):
    slack, mid = FakeSlack(), saved(priority=priority)
    deliver_slack_alert(conn, get_message(conn, mid), slack)
    assert slack.alerts == [] and slack.calls == 0
    assert not get_message(conn, mid).slack_sent


def test_priority_four_is_the_alert_threshold(conn, saved):
    slack, mid = FakeSlack(), saved(priority=4)
    deliver_slack_alert(conn, get_message(conn, mid), slack)
    assert slack.alerts == [mid]


def test_slack_down_leaves_flag_false_so_retry_can_send(conn, saved):
    slack, mid = FakeSlack(fail_times=1), saved(priority=5)
    with pytest.raises(ConnectionError):
        deliver_slack_alert(conn, get_message(conn, mid), slack)
    assert not get_message(conn, mid).slack_sent
    deliver_slack_alert(conn, get_message(conn, mid), slack)
    assert slack.alerts == [mid]


def test_delivery_without_a_card_is_an_error(conn):
    r = register_message(conn, "a@x.com", "hello", "form")
    with pytest.raises(ValueError):
        deliver_to_sheet(conn, get_message(conn, r.message_id), FakeSheets())


def test_card_json_round_trips_through_postgres(conn, saved):
    stored = get_message(conn, saved()).card_json
    assert LeadCard.model_validate(stored) == LeadCard.model_validate(json.loads(GOOD_CARD))
