from concurrent.futures import ThreadPoolExecutor

from app.db import Status, claim_message, connect, get_message, register_message, release_message
from app.pipeline import fill_from_form, process_message
from app.schemas import LeadCard
from tests.conftest import GOOD_CARD, TEST_URL
from tests.fakes import FakeSheets, FakeSlack
from tests.test_pipeline import NO_WAIT, extraction


def new_message(conn, sender="raj@acme.com", name=None) -> int:
    return register_message(conn, sender, "need a website", "form", name=name).message_id


def test_only_the_first_claim_wins(conn):
    mid = new_message(conn)
    assert claim_message(conn, mid) is True
    assert claim_message(conn, mid) is False  # someone already holds it


def test_expired_claim_can_be_taken_over(conn):
    mid = new_message(conn)
    claim_message(conn, mid)
    conn.execute(
        "UPDATE messages SET locked_until = now() - interval '1 second' WHERE id = %s", (mid,)
    )
    assert claim_message(conn, mid) is True  # the first worker crashed; lease ran out


def test_released_claim_can_be_taken_again(conn):
    mid = new_message(conn)
    claim_message(conn, mid)
    release_message(conn, mid)
    assert claim_message(conn, mid) is True


def test_finished_messages_cannot_be_claimed(conn):
    mid = new_message(conn)
    conn.execute("UPDATE messages SET status = 'delivered' WHERE id = %s", (mid,))
    assert claim_message(conn, mid) is False


def test_ten_workers_at_once_exactly_one_wins(conn):
    """Real parallel database connections all trying to claim the same message."""
    mid = new_message(conn)

    def try_claim(_):
        c = connect(TEST_URL)
        try:
            return claim_message(c, mid)
        finally:
            c.close()

    with ThreadPoolExecutor(max_workers=10) as pool:
        results = list(pool.map(try_claim, range(10)))
    assert results.count(True) == 1


def test_worker_that_cannot_claim_does_nothing(conn):
    mid = new_message(conn)
    claim_message(conn, mid)  # worker 1 holds it
    ai_calls = []
    sheets, slack = FakeSheets(), FakeSlack()

    def spy(text):
        ai_calls.append(1)
        return extraction()

    status = process_message(conn, mid, sheets, slack, spy, NO_WAIT)  # worker 2
    assert status is Status.RECEIVED
    assert ai_calls == [] and sheets.rows == {} and slack.alerts == []


def test_lock_is_released_when_the_worker_finishes(conn):
    mid = new_message(conn)
    process_message(conn, mid, FakeSheets(), FakeSlack(), lambda t: extraction(), NO_WAIT)
    assert (
        conn.execute("SELECT locked_until FROM messages WHERE id = %s", (mid,)).fetchone()[0]
        is None
    )


def test_lock_is_released_even_when_the_worker_gives_up(conn):
    mid = new_message(conn)
    process_message(
        conn, mid, FakeSheets(fail_times=99), FakeSlack(), lambda t: extraction(), NO_WAIT
    )
    assert (
        conn.execute("SELECT locked_until FROM messages WHERE id = %s", (mid,)).fetchone()[0]
        is None
    )


def test_sender_details_are_stored_with_the_message(conn):
    msg = get_message(conn, new_message(conn, "sam@mail.com", "Sam"))
    assert (msg.sender_email, msg.sender_name) == ("sam@mail.com", "Sam")


def card(**kw) -> LeadCard:
    return LeadCard.model_validate_json(GOOD_CARD).model_copy(update=kw)


def test_form_email_and_name_fill_gaps_the_message_text_left():
    c = fill_from_form(card(email=None, name=None), "sam@mail.com", "Sam")
    assert (c.email, c.name) == ("sam@mail.com", "Sam")


def test_details_found_in_the_text_are_kept():
    c = fill_from_form(card(email="found@text.com", name="Raj M"), "form@x.com", "Form Name")
    assert (c.email, c.name) == ("found@text.com", "Raj M")


def test_junk_form_email_is_not_copied_in():
    assert fill_from_form(card(email=None), "not an email", None).email is None


def test_pipeline_saves_the_filled_card(conn):
    mid = new_message(conn, "sam@mail.com", "Sam")
    process_message(
        conn, mid, FakeSheets(), FakeSlack(),
        lambda t: extraction(2).__class__(**{**extraction(2).__dict__, "card": card(email=None, name=None, priority=2)}),
        NO_WAIT,
    )  # fmt: skip
    saved = get_message(conn, mid).card_json
    assert saved["email"] == "sam@mail.com" and saved["name"] == "Sam"
