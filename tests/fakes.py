"""Stand-ins for Google Sheets and Slack. They record what was sent and can be told to fail."""

from app.schemas import LeadCard


class FakeSheets:
    def __init__(self, fail_times: int = 0, fail_after_write: bool = False):
        self.rows: dict[int, LeadCard] = {}
        self.calls = 0
        self.fail_times = fail_times
        self.fail_after_write = fail_after_write  # write succeeds, but the reply is 'lost'

    def append_lead(self, message_id, received_at, source, card):
        self.calls += 1
        if message_id not in self.rows:  # same rule as the real writer: id already there? skip
            self.rows[message_id] = card
        if self.fail_after_write and self.calls <= self.fail_times:
            raise TimeoutError("reply lost after the row was written")
        if not self.fail_after_write and self.calls <= self.fail_times:
            del self.rows[message_id]
            raise ConnectionError("sheets down")


class FakeSlack:
    def __init__(self, fail_times: int = 0):
        self.alerts: list[int] = []
        self.calls = 0
        self.fail_times = fail_times

    def post_alert(self, message_id, card):
        self.calls += 1
        if self.calls <= self.fail_times:
            raise ConnectionError("slack down")
        self.alerts.append(message_id)
