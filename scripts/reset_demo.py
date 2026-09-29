"""Wipe demo data so the next demo run starts clean: all Postgres tables AND the Sheet's rows.

    uv run python scripts/reset_demo.py --yes

Both are cleared together on purpose. The Sheet skips any message id it already has, and the
database restarts ids at 1 after a reset - clearing only one side makes new messages silently
collide with old rows (the id-reuse gotcha in the README).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import connect, init_db
from app.sheets import GoogleSheets

if __name__ == "__main__":
    if "--yes" not in sys.argv:
        sys.exit(
            "This deletes ALL messages, approvals, DLQ items and Sheet rows. Re-run with --yes."
        )

    conn = connect()
    init_db(conn)
    conn.execute("TRUNCATE messages, approvals, dlq RESTART IDENTITY CASCADE")
    print("database: cleared")

    ws = GoogleSheets().ws
    rows = len(ws.get_all_values())
    if rows > 1:
        ws.delete_rows(2, rows)  # keep the header row
    print(f"sheet: cleared {max(rows - 1, 0)} row(s)")
