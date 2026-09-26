import httpx

from app.schemas import LeadCard
from app.settings import settings


class SlackNotifier:
    """Posts hot-lead alerts through the incoming webhook."""

    def post_alert(self, message_id: int, card: LeadCard) -> None:
        who = ", ".join(x for x in (card.name, card.company) if x) or "Unknown sender"
        text = (
            f":fire: *Hot lead* (priority {card.priority}) #{message_id}\n"
            f"*{who}*  {card.email or ''}\n"
            f"{card.intent}\n_{card.reason}_"
        )
        r = httpx.post(settings.slack_webhook_url, json={"text": text}, timeout=10)
        r.raise_for_status()  # 4xx/5xx becomes an exception the retry logic can act on
