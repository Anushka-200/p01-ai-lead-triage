"""Send a saved card to Sheets and Slack, once each, however many times this is called."""

import psycopg

from app.db import Message, mark_sheet_written, mark_slack_sent
from app.ports import SheetsPort, SlackPort
from app.schemas import LeadCard
from app.settings import settings


def card_of(msg: Message) -> LeadCard:
    if msg.card_json is None:
        raise ValueError(f"message {msg.id} has no card yet")
    return LeadCard.model_validate(msg.card_json)


def deliver_to_sheet(conn: psycopg.Connection, msg: Message, sheets: SheetsPort) -> None:
    if msg.sheet_written:  # already done on an earlier attempt
        return
    sheets.append_lead(msg.id, msg.received_at.isoformat(), msg.source, card_of(msg))
    mark_sheet_written(conn, msg.id)


def deliver_slack_alert(conn: psycopg.Connection, msg: Message, slack: SlackPort) -> None:
    card = card_of(msg)
    if msg.slack_sent or card.priority < settings.hot_lead_priority:
        return
    slack.post_alert(msg.id, card)
    mark_slack_sent(conn, msg.id)
