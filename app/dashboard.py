"""Priya's dashboard: last 50 messages, held approvals, and the DLQ shelf.

uv run streamlit run app/dashboard.py
"""

import json
import sys
from pathlib import Path

# `streamlit run app/dashboard.py` executes this file as a standalone script, so Python only
# looks inside app/ by default. Add the project root so `import app.db` etc. can be found,
# the same way `uv run pytest` and PYTHONPATH=. already do for the other entry points.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

from app.db import (
    connect,
    decide_approval,
    list_open_dlq,
    list_pending_approvals,
    recent_messages,
)
from app.pipeline import decide, replay
from app.settings import settings
from app.sheets import GoogleSheets
from app.slack import SlackNotifier

st.set_page_config(page_title="P01 Lead Triage", page_icon=":envelope:", layout="wide")


def check_password() -> bool:
    """A shared password, not a per-user login. Fine for one internal user; a real client
    with several staff would need proper accounts instead."""
    if not settings.dashboard_password:
        st.error("DASHBOARD_PASSWORD is not set in .env. Refusing to run unprotected.")
        st.stop()
    if st.session_state.get("authed"):
        return True
    entered = st.text_input("Password", type="password")
    if entered and entered == settings.dashboard_password:
        st.session_state["authed"] = True
        st.rerun()
    elif entered:
        st.error("Wrong password.")
    return False


@st.cache_resource
def outputs():
    return GoogleSheets(), SlackNotifier()


def card_text(card_json) -> dict:
    return json.loads(card_json) if isinstance(card_json, str) else (card_json or {})


def approvals_tab(conn):
    rows = list_pending_approvals(conn)
    st.subheader(f"Waiting for a decision ({len(rows)})")
    if not rows:
        st.caption("Nothing held right now.")
    for approval_id, message_id, raw_text, card_json, received in rows:
        card = card_text(card_json)
        with st.container(border=True):
            st.write(
                f"**#{message_id}** · {received:%Y-%m-%d %H:%M} · priority {card.get('priority')}"
            )
            st.write(f"{card.get('name') or 'Unknown'} · {card.get('email') or ''}")
            st.write(f"*{card.get('reason')}*")
            with st.expander("Original message"):
                st.text(raw_text)
            c1, c2 = st.columns(2)
            sheets, slack = outputs()
            if c1.button("Approve", key=f"a{approval_id}"):
                status = decide(conn, approval_id, True, sheets, slack)
                st.toast(f"Message {message_id}: {status.value if status else 'already decided'}")
                st.rerun()
            if c2.button("Reject", key=f"r{approval_id}"):
                decide_approval(conn, approval_id, False)
                st.toast(f"Message {message_id}: rejected")
                st.rerun()


def messages_tab(conn):
    rows = recent_messages(conn, 50)
    st.subheader(f"Last {len(rows)} messages")
    for mid, status, source, received, card_json, sender in rows:
        card = card_text(card_json)
        badge = {
            "delivered": ":green_circle:",
            "failed": ":red_circle:",
            "waiting_approval": ":large_orange_circle:",
        }
        st.write(
            f"{badge.get(status, ':white_circle:')} **#{mid}** {received:%m-%d %H:%M} "
            f"[{source}] {status} · p{card.get('priority', '-')} {card.get('category', '')} "
            f"· {sender or ''}"
        )


def dlq_tab(conn):
    rows = list_open_dlq(conn)
    st.subheader(f"Dead-letter queue ({len(rows)})")
    if not rows:
        st.caption("Nothing stuck.")
    for dlq_id, message_id, stage, error, attempts, created in rows:
        with st.container(border=True):
            st.write(
                f"**#{dlq_id}** message {message_id} · stage `{stage}` · {attempts} attempts · {created:%m-%d %H:%M}"
            )
            st.code(error, language=None)
            if st.button("Replay", key=f"rp{dlq_id}"):
                sheets, slack = outputs()
                status = replay(conn, dlq_id, sheets, slack)
                st.toast(f"Replay of #{dlq_id}: {status.value}")
                st.rerun()


def main() -> None:
    st.title(":envelope: P01 Lead Triage")
    if not check_password():
        st.stop()
    conn = connect()
    tab1, tab2, tab3 = st.tabs(["Approvals", "Messages", "DLQ"])
    with tab1:
        approvals_tab(conn)
    with tab2:
        messages_tab(conn)
    with tab3:
        dlq_tab(conn)


if __name__ == "__main__":
    main()
