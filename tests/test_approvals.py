from app.db import Status, get_message, list_pending_approvals, register_message
from app.pipeline import decide, process_message
from tests.fakes import FakeSheets, FakeSlack
from tests.test_pipeline import NO_WAIT, extraction


def held_message(conn, priority=5):
    """A message that's already gone through the pipeline and is sitting in the approval queue."""
    mid = register_message(conn, "meera@shop.in", "refund please", "form").message_id
    process_message(
        conn,
        mid,
        FakeSheets(),
        FakeSlack(),
        lambda t: extraction(priority, "refund_complaint"),
        NO_WAIT,
    )
    (row,) = [r for r in list_pending_approvals(conn) if r[1] == mid]
    return row[0], mid  # approval_id, message_id


def test_pending_list_shows_held_messages(conn):
    _, mid = held_message(conn)
    rows = list_pending_approvals(conn)
    assert [r[1] for r in rows] == [mid]


def test_approve_hot_lead_delivers_and_alerts(conn):
    approval_id, mid = held_message(conn, priority=5)
    sheets, slack = FakeSheets(), FakeSlack()
    status = decide(conn, approval_id, True, sheets, slack, NO_WAIT)
    assert status is Status.DELIVERED
    assert list(sheets.rows) == [mid] and slack.alerts == [mid]
    assert get_message(conn, mid).status is Status.DELIVERED


def test_approve_low_priority_delivers_without_alert(conn):
    approval_id, mid = held_message(conn, priority=2)
    sheets, slack = FakeSheets(), FakeSlack()
    decide(conn, approval_id, True, sheets, slack, NO_WAIT)
    assert list(sheets.rows) == [mid] and slack.alerts == []


def test_reject_sends_nothing_and_marks_rejected(conn):
    approval_id, mid = held_message(conn)
    sheets, slack = FakeSheets(), FakeSlack()
    status = decide(conn, approval_id, False, sheets, slack, NO_WAIT)
    assert status is Status.REJECTED
    assert sheets.rows == {} and slack.alerts == []
    assert get_message(conn, mid).status is Status.REJECTED


def test_approval_record_itself_is_updated(conn):
    approval_id, _ = held_message(conn)
    decide(conn, approval_id, True, FakeSheets(), FakeSlack(), NO_WAIT)
    status = conn.execute("SELECT status FROM approvals WHERE id = %s", (approval_id,)).fetchone()[
        0
    ]
    assert status == "approved"


def test_deciding_twice_the_second_time_is_a_no_op(conn):
    approval_id, mid = held_message(conn)
    sheets, slack = FakeSheets(), FakeSlack()
    decide(conn, approval_id, True, sheets, slack, NO_WAIT)
    second = decide(
        conn, approval_id, False, sheets, slack, NO_WAIT
    )  # double click, different button
    assert second is None
    assert get_message(conn, mid).status is Status.DELIVERED  # first decision stands
    assert sheets.calls == 1  # not delivered twice either


def test_unknown_approval_id_is_a_no_op(conn):
    assert decide(conn, 999, True, FakeSheets(), FakeSlack(), NO_WAIT) is None


def test_approved_delivery_that_fails_goes_to_dlq(conn):
    from app.db import list_open_dlq

    approval_id, mid = held_message(conn, priority=5)
    status = decide(conn, approval_id, True, FakeSheets(fail_times=99), FakeSlack(), NO_WAIT)
    assert status is Status.FAILED
    assert get_message(conn, mid).status is Status.FAILED
    assert list_open_dlq(conn)[0][2] == "sheets"
