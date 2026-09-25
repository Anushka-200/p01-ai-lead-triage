import litellm

from app.prompts import SYSTEM_PROMPT, build_user_message
from app.schemas import LeadCard
from app.settings import settings

# The "blank form" we hand the model. It must answer by calling this tool.
LEAD_TOOL = {
    "type": "function",
    "function": {
        "name": "record_lead",
        "description": "Record the lead card for the message.",
        "parameters": LeadCard.model_json_schema(),
    },
}


def call_model(messages: list[dict], model: str) -> str:
    """One LLM call. Returns the raw JSON text the model put in the form."""
    resp = litellm.completion(
        model=model,
        messages=messages,
        tools=[LEAD_TOOL],
        tool_choice={"type": "function", "function": {"name": "record_lead"}},
        timeout=settings.llm_timeout_s,
        api_key=settings.anthropic_api_key,
        temperature=0,
    )
    return resp.choices[0].message.tool_calls[0].function.arguments


def extract_card(text: str, model: str | None = None) -> LeadCard:
    model = model or settings.cheap_model
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_message(text)},
    ]
    raw = call_model(messages, model)
    return LeadCard.model_validate_json(raw)  # raises ValidationError if the form is wrong
