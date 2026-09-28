from app import extractor
from app.extractor import extract_card
from app.schemas import LeadCard
from app.settings import settings
from tests.conftest import GOOD_CARD


def card_with_confidence(c: float) -> LeadCard:
    return LeadCard.model_validate_json(GOOD_CARD).model_copy(update={"confidence": c})


def fake_extract_once(monkeypatch, responses: dict[str, tuple]):
    """responses maps model name -> (card, tokens_in, tokens_out, cost, attempts)."""
    calls = []

    def fake(text, model):
        calls.append(model)
        return responses[model]

    monkeypatch.setattr(extractor, "_extract_once", fake)
    return calls


def test_confident_haiku_answer_is_not_routed(monkeypatch):
    calls = fake_extract_once(
        monkeypatch, {settings.cheap_model: (card_with_confidence(0.95), 100, 50, 0.002, 1)}
    )
    result = extract_card("hello")
    assert calls == [settings.cheap_model]  # Sonnet never called
    assert not result.routed and result.model == settings.cheap_model


def test_unsure_haiku_answer_is_escalated_to_sonnet(monkeypatch):
    calls = fake_extract_once(
        monkeypatch,
        {
            settings.cheap_model: (card_with_confidence(0.4), 100, 50, 0.002, 1),
            settings.escalation_model: (card_with_confidence(0.9), 300, 80, 0.02, 1),
        },
    )
    result = extract_card("hello")
    assert calls == [settings.cheap_model, settings.escalation_model]
    assert result.routed and result.model == settings.escalation_model
    assert result.card.confidence == 0.9  # Sonnet's answer wins, not Haiku's


def test_routed_call_sums_tokens_and_cost_from_both_models(monkeypatch):
    fake_extract_once(
        monkeypatch,
        {
            settings.cheap_model: (card_with_confidence(0.4), 100, 50, 0.002, 1),
            settings.escalation_model: (card_with_confidence(0.9), 300, 80, 0.02, 2),
        },
    )
    result = extract_card("hello")
    assert (result.tokens_in, result.tokens_out) == (400, 130)
    assert result.cost_usd == 0.022
    assert result.attempts == 3  # 1 (Haiku) + 2 (Sonnet's own repair attempts)


def test_confidence_exactly_at_threshold_is_not_routed(monkeypatch):
    threshold = settings.routing_confidence_threshold
    calls = fake_extract_once(
        monkeypatch, {settings.cheap_model: (card_with_confidence(threshold), 100, 50, 0.002, 1)}
    )
    extract_card("hello")
    assert calls == [settings.cheap_model]


def test_forcing_a_specific_model_disables_routing(monkeypatch):
    """extract_card(text, model=...) is used by tests elsewhere and must stay single-call."""
    calls = fake_extract_once(
        monkeypatch, {settings.escalation_model: (card_with_confidence(0.1), 300, 80, 0.02, 1)}
    )
    result = extract_card("hello", model=settings.escalation_model)
    assert calls == [settings.escalation_model]  # low confidence, but no auto-escalation happens
    assert not result.routed
