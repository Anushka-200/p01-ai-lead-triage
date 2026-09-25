from contextlib import nullcontext

import pytest

from app import extractor
from app.extractor import LLMReply

GOOD_CARD = (
    '{"name":"Raj","email":"raj@acme.com","company":"Acme","intent":"Marketing strategy",'
    '"category":"new_lead","priority":4,"reason":"Clear need and budget","confidence":0.9}'
)
BAD_PRIORITY = GOOD_CARD.replace('"priority":4', '"priority":9')


def reply(raw: str, tokens_in: int = 100, tokens_out: int = 50, cost: float = 0.001) -> LLMReply:
    return LLMReply(raw=raw, tokens_in=tokens_in, tokens_out=tokens_out, cost_usd=cost)


@pytest.fixture(autouse=True)
def no_tracing(monkeypatch):
    """Tests must never send traces to Langfuse."""
    monkeypatch.setattr(extractor, "observation", lambda **kw: nullcontext(None))


@pytest.fixture
def fake_model(monkeypatch):
    """Replace the real AI call with a scripted list of replies. Returns the list of calls made."""

    def install(replies: list[LLMReply]):
        calls: list[list[dict]] = []
        queue = iter(replies)

        def fake_call(messages, model):
            calls.append(messages)
            return next(queue)

        monkeypatch.setattr(extractor, "call_model", fake_call)
        return calls

    return install
