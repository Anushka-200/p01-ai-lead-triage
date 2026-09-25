from dataclasses import dataclass

import litellm
from pydantic import ValidationError

from app.prompts import PROMPT_VERSION, SYSTEM_PROMPT, build_user_message
from app.schemas import LeadCard
from app.settings import settings
from app.tracing import observation

# The "blank form" we hand the model. It must answer by calling this tool.
LEAD_TOOL = {
    "type": "function",
    "function": {
        "name": "record_lead",
        "description": "Record the lead card for the message.",
        "parameters": LeadCard.model_json_schema(),
    },
}


class ExtractionError(Exception):
    """The model could not produce a valid card, even after repair attempts. -> DLQ."""


@dataclass
class LLMReply:
    raw: str  # JSON text the model put in the form ("" if it ignored the form)
    tokens_in: int
    tokens_out: int
    cost_usd: float


@dataclass
class Extraction:
    card: LeadCard
    model: str
    prompt_version: str
    attempts: int
    tokens_in: int
    tokens_out: int
    cost_usd: float


def call_model(messages: list[dict], model: str) -> LLMReply:
    """One LLM call, traced. Retries for network errors come later (retry.py, ADR 004)."""
    with observation(name="llm-call", as_type="generation", model=model, input=messages) as gen:
        resp = litellm.completion(
            model=model,
            messages=messages,
            tools=[LEAD_TOOL],
            tool_choice={"type": "function", "function": {"name": "record_lead"}},
            timeout=settings.llm_timeout_s,
            api_key=settings.anthropic_api_key,
            temperature=0,
        )
        tool_calls = resp.choices[0].message.tool_calls
        reply = LLMReply(
            raw=tool_calls[0].function.arguments if tool_calls else "",
            tokens_in=resp.usage.prompt_tokens,
            tokens_out=resp.usage.completion_tokens,
            cost_usd=litellm.completion_cost(completion_response=resp),
        )
        if gen is not None:
            gen.update(
                output=reply.raw,
                usage_details={"input": reply.tokens_in, "output": reply.tokens_out},
                cost_details={"total": reply.cost_usd},
            )
        return reply


def extract_card(text: str, model: str | None = None) -> Extraction:
    """Message text -> validated LeadCard. Invalid answer? Tell the model why and retry."""
    model = model or settings.cheap_model
    base = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_message(text)},
    ]
    messages = base
    tokens_in = tokens_out = 0
    cost = 0.0
    last_error = ""

    with observation(
        name="extract_card", metadata={"prompt_version": PROMPT_VERSION, "model": model}
    ):
        for attempt in range(1, settings.max_repairs + 2):
            reply = call_model(messages, model)
            tokens_in += reply.tokens_in
            tokens_out += reply.tokens_out
            cost += reply.cost_usd
            try:
                card = LeadCard.model_validate_json(reply.raw)
                return Extraction(card, model, PROMPT_VERSION, attempt, tokens_in, tokens_out, cost)
            except ValidationError as e:
                # Keep the error short: field names and what was wrong, nothing else.
                problems = "; ".join(
                    f"{'.'.join(map(str, x['loc']))}: {x['msg']}" for x in e.errors()
                )
                last_error = problems if reply.raw else "you did not fill in the record_lead form"
                messages = base + [
                    {
                        "role": "user",
                        "content": (
                            f"Your previous answer was invalid ({last_error}). "
                            f"Previous answer: {reply.raw or '(none)'}\n"
                            "Call record_lead again with every field valid."
                        ),
                    }
                ]
    raise ExtractionError(f"invalid after {settings.max_repairs + 1} attempts: {last_error}")
