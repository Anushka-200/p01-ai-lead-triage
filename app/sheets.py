import gspread

from app.schemas import LeadCard
from app.settings import settings

HEADER = [
    "message_id", "received_at", "source", "name", "email", "company",
    "category", "priority", "intent", "reason", "confidence",
]  # fmt: skip


class GoogleSheets:
    """Writes one row per lead. Safe to call twice: the message id is checked first."""

    def __init__(self) -> None:
        gc = gspread.service_account(filename=settings.google_service_account_file)
        self.ws = gc.open_by_key(settings.google_sheet_id).sheet1

    def _ensure_header(self) -> None:
        if not self.ws.row_values(1):
            self.ws.insert_row(HEADER, 1)

    def append_lead(self, message_id: int, received_at: str, source: str, card: LeadCard) -> None:
        self._ensure_header()
        # Idempotency: a retry after a timeout must not add a second row.
        if str(message_id) in self.ws.col_values(1):
            return
        self.ws.append_row(
            [
                message_id, received_at, source, card.name or "", card.email or "",
                card.company or "", card.category.value, card.priority, card.intent,
                card.reason, card.confidence,
            ],
            value_input_option="RAW",  # store text as-is; never let Sheets run a '=formula'
        )  # fmt: skip
