"""Look at the dead-letter shelf and replay items.

uv run python -m app.dlq_cli list
uv run python -m app.dlq_cli replay 3
uv run python -m app.dlq_cli replay --all
"""

import argparse

from app.db import connect, list_open_dlq
from app.logging_setup import configure_logging
from app.pipeline import open_dlq_ids, replay
from app.sheets import GoogleSheets
from app.slack import SlackNotifier


def main() -> None:
    configure_logging()
    parser = argparse.ArgumentParser(description="Dead-letter queue tools")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list", help="show items still waiting")
    rp = sub.add_parser("replay", help="retry items once the problem is fixed")
    rp.add_argument("dlq_id", nargs="?", type=int)
    rp.add_argument("--all", action="store_true")
    args = parser.parse_args()

    conn = connect()
    if args.cmd == "list":
        rows = list_open_dlq(conn)
        if not rows:
            print("DLQ is empty.")
        for id_, mid, stage, error, attempts, created in rows:
            print(
                f"#{id_}  message {mid}  stage={stage}  tries={attempts}  {created:%Y-%m-%d %H:%M}  {error[:80]}"
            )
        return

    ids = open_dlq_ids(conn) if args.all else [args.dlq_id]
    if ids == [None]:
        parser.error("give a DLQ id or --all")
    sheets, slack = GoogleSheets(), SlackNotifier()
    for dlq_id in ids:
        print(f"#{dlq_id}: {replay(conn, dlq_id, sheets, slack).value}")


if __name__ == "__main__":
    main()
