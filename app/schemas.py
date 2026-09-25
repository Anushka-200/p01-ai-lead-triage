from enum import Enum

from pydantic import BaseModel, Field, field_validator


class Category(str, Enum):
    NEW_LEAD = "new_lead"
    SUPPORT = "support"
    REFUND_COMPLAINT = "refund_complaint"  # sensitive: held for human approval
    SPAM = "spam"
    OTHER = "other"


class LeadCard(BaseModel):
    """The form the AI fills in for every message."""

    name: str | None = Field(None, description="Sender's name, null if not stated")
    email: str | None = Field(None, description="Sender's email, null if not stated")
    company: str | None = Field(None, description="Sender's company, null if not stated")
    intent: str = Field(max_length=200, description="What the sender wants, in one short sentence")
    category: Category
    priority: int = Field(ge=1, le=5, description="1 = ignore, 5 = reply today")
    reason: str = Field(max_length=300, description="One line: why this priority")
    confidence: float = Field(ge=0, le=1, description="How sure you are, 0 to 1")

    @field_validator("email")
    @classmethod
    def email_looks_valid(cls, v: str | None) -> str | None:
        # Light check on purpose: the LLM may only copy an address that is in the message.
        if v is not None and ("@" not in v or " " in v):
            raise ValueError("email must contain '@' and no spaces")
        return v
