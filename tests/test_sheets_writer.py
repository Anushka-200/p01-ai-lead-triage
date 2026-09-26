import threading
import time

from gspread.utils import InsertDataOption

from app.schemas import LeadCard
from app.sheets import GoogleSheets
from tests.conftest import GOOD_CARD


class FakeWorksheet:
    """Records how append_row is called, and whether two calls ever overlap."""

    def __init__(self):
        self.ids: list[str] = []
        self.options = []
        self.active = 0
        self.max_active = 0

    def row_values(self, n):
        return ["header"]

    def col_values(self, n):
        return list(self.ids)

    def append_row(self, values, **kwargs):
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        time.sleep(0.02)  # a slow network call
        self.ids.append(str(values[0]))
        self.options.append(kwargs.get("insert_data_option"))
        self.active -= 1


def writer(ws) -> GoogleSheets:
    g = GoogleSheets.__new__(GoogleSheets)  # skip the real Google login
    g.ws = ws
    return g


CARD = LeadCard.model_validate_json(GOOD_CARD)


def test_rows_are_always_inserted_never_overwritten():
    ws = FakeWorksheet()
    writer(ws).append_lead(1, "t", "form", CARD)
    assert ws.options == [InsertDataOption.insert_rows]


def test_parallel_writers_take_turns_and_no_row_is_lost():
    ws = FakeWorksheet()
    g = writer(ws)
    threads = [
        threading.Thread(target=g.append_lead, args=(i, "t", "form", CARD)) for i in range(1, 9)
    ]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert ws.max_active == 1  # never two appends at once
    assert sorted(ws.ids, key=int) == [str(i) for i in range(1, 9)]


def test_existing_message_id_is_not_written_again():
    ws = FakeWorksheet()
    g = writer(ws)
    g.append_lead(5, "t", "form", CARD)
    g.append_lead(5, "t", "form", CARD)
    assert ws.ids == ["5"]
