"""Finish messages that were saved but never processed (run after a crash or restart).

uv run python -m app.sweep
"""

from app.db import connect
from app.pipeline import process_message, stale_message_ids
from app.sheets import GoogleSheets
from app.slack import SlackNotifier

if __name__ == "__main__":
    conn = connect()
    ids = stale_message_ids(conn)
    print(f"{len(ids)} unfinished message(s)")
    sheets, slack = GoogleSheets(), SlackNotifier()
    for mid in ids:
        print(f"message {mid}: {process_message(conn, mid, sheets, slack).value}")
