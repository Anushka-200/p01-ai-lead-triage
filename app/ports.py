"""Small interfaces for the outside world. Real versions call Google/Slack; tests use fakes."""

from typing import Protocol

from app.schemas import LeadCard


class SheetsPort(Protocol):
    def append_lead(self, message_id: int, received_at: str, source: str, card: LeadCard) -> None:
        """Add a row. Must do nothing if a row for message_id already exists."""


class SlackPort(Protocol):
    def post_alert(self, message_id: int, card: LeadCard) -> None:
        """Post one alert message. Raises on failure."""
