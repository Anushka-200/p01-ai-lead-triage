"""Look at held messages and approve or reject them (until the dashboard exists).

uv run python -m app.approvals_cli list
uv run python -m app.approvals_cli approve 2
uv run python -m app.approvals_cli reject 2
"""

import argparse
import json

from app.db import connect, list_pending_approvals
from app.pipeline import decide
from app.sheets import GoogleSheets
from app.slack import SlackNotifier


def main() -> None:
    parser = argparse.ArgumentParser(description="Approve or reject held messages")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list", help="show messages waiting for a decision")
    for name in ("approve", "reject"):
        p = sub.add_parser(name)
        p.add_argument("approval_id", type=int)
    args = parser.parse_args()

    conn = connect()
    if args.cmd == "list":
        rows = list_pending_approvals(conn)
        if not rows:
            print("No messages waiting for approval.")
        for approval_id, message_id, _text, card_json, received in rows:
            card = json.loads(card_json) if isinstance(card_json, str) else card_json
            who = card.get("name") or card.get("email") or "unknown sender"
            print(
                f"#{approval_id}  message {message_id}  {received:%Y-%m-%d %H:%M}  {who}: {card.get('reason')}"
            )
        return

    sheets, slack = GoogleSheets(), SlackNotifier()
    status = decide(conn, args.approval_id, args.cmd == "approve", sheets, slack)
    print("already decided" if status is None else status.value)


if __name__ == "__main__":
    main()
