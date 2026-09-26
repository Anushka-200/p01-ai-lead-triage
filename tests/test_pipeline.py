import pytest

from app.db import Status, get_message, list_open_dlq, register_message
from app.extractor import Extraction, ExtractionError
from app.pipeline import process_message, replay
from app.schemas import LeadCard
from tests.conftest import GOOD_CARD
from tests.fakes import FakeSheets, FakeSlack

NO_WAIT = lambda s: None


def extraction(priority: int = 4, category: str = "new_lead") -> Extraction:
    raw = GOOD_CARD.replace('"priority":4', f'"priority":{priority}')
    raw = raw.replace('"category":"new_lead"', f'"category":"{category}"')
    return Extraction(LeadCard.model_validate_json(raw), "haiku", "v1", 1, 100, 50, 0.001)


def new_message(conn, text="need a website") -> int:
    return register_message(conn, "raj@acme.com", text, "form").message_id


def run(conn, mid, sheets=None, slack=None, extract=None):
    sheets, slack = sheets or FakeSheets(), slack or FakeSlack()
    extract = extract or (lambda text: extraction())
    return process_message(conn, mid, sheets, slack, extract, NO_WAIT), sheets, slack


def test_happy_path_delivers_row_and_alert(conn):
    mid = new_message(conn)
    status, sheets, slack = run(conn, mid)
    assert status is Status.DELIVERED
    assert list(sheets.rows) == [mid] and slack.alerts == [mid]
    assert get_message(conn, mid).card_json["priority"] == 4


def test_low_priority_is_logged_without_alert(conn):
    mid = new_message(conn)
    status, sheets, slack = run(conn, mid, extract=lambda t: extraction(priority=2))
    assert status is Status.DELIVERED and list(sheets.rows) == [mid] and slack.alerts == []


def test_refund_complaint_waits_for_approval_and_sends_nothing(conn):
    mid = new_message(conn)
    status, sheets, slack = run(conn, mid, extract=lambda t: extraction(5, "refund_complaint"))
    assert status is Status.WAITING_APPROVAL
    assert sheets.rows == {} and slack.alerts == []
    assert (
        conn.execute("SELECT status FROM approvals WHERE message_id = %s", (mid,)).fetchone()[0]
        == "pending"
    )


def test_running_twice_does_not_duplicate_anything(conn):
    mid = new_message(conn)
    _, sheets, slack = run(conn, mid)
    status, _, _ = run(conn, mid, sheets, slack)
    assert status is Status.DELIVERED and sheets.calls == 1 and slack.alerts == [mid]


def test_slack_down_retries_then_dlq_and_sheet_row_is_kept(conn):
    mid = new_message(conn)
    slack = FakeSlack(fail_times=99)
    status, sheets, _ = run(conn, mid, slack=slack)
    assert status is Status.FAILED
    assert slack.calls == 4  # 4 attempts, then stop
    assert list(sheets.rows) == [mid]  # the sheet part had already succeeded
    (item,) = list_open_dlq(conn)
    assert item[2] == "slack" and item[4] == 4


def test_replay_after_slack_recovers_delivers_without_duplicating(conn):
    mid = new_message(conn)
    slack = FakeSlack(fail_times=4)  # down for the first 4 calls only
    _, sheets, _ = run(conn, mid, slack=slack)
    (item,) = list_open_dlq(conn)
    status = replay(conn, item[0], sheets, slack, lambda t: extraction(), NO_WAIT)
    assert status is Status.DELIVERED
    assert slack.alerts == [mid] and list(sheets.rows) == [mid]
    assert list_open_dlq(conn) == []  # shelf is empty again


def test_sheets_down_goes_to_dlq_and_no_alert_is_sent(conn):
    mid = new_message(conn)
    status, _, slack = run(conn, mid, sheets=FakeSheets(fail_times=99))
    assert status is Status.FAILED and slack.alerts == []
    assert list_open_dlq(conn)[0][2] == "sheets"


def test_invalid_extraction_goes_to_dlq_without_retrying(conn):
    mid = new_message(conn)
    calls = []

    def bad(text):
        calls.append(1)
        raise ExtractionError("invalid after 3 attempts")

    status, sheets, slack = run(conn, mid, extract=bad)
    assert status is Status.FAILED and len(calls) == 1
    assert sheets.rows == {} and slack.alerts == []
    assert list_open_dlq(conn)[0][2] == "extract"


def test_temporary_ai_outage_is_retried_and_succeeds(conn):
    mid = new_message(conn)
    calls = []

    def flaky(text):
        calls.append(1)
        if len(calls) < 3:
            raise TimeoutError("model timed out")
        return extraction()

    status, sheets, _ = run(conn, mid, extract=flaky)
    assert status is Status.DELIVERED and len(calls) == 3 and list(sheets.rows) == [mid]


def test_crash_after_extraction_resumes_without_asking_the_ai_again(conn):
    mid = new_message(conn)
    run(conn, mid, sheets=FakeSheets(fail_times=99))  # fails at sheets, card is saved
    calls = []

    def must_not_be_called(text):
        calls.append(1)
        return extraction()

    (item,) = list_open_dlq(conn)
    status = replay(conn, item[0], FakeSheets(), FakeSlack(), must_not_be_called, NO_WAIT)
    assert status is Status.DELIVERED and calls == []  # no second AI bill


def test_replay_of_unknown_item_raises(conn):
    with pytest.raises(KeyError):
        replay(conn, 999, FakeSheets(), FakeSlack())
