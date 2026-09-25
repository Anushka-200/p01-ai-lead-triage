import pytest
from pydantic import ValidationError

from app.schemas import Category, LeadCard
from tests.conftest import BAD_PRIORITY, GOOD_CARD


def test_valid_card_is_accepted():
    card = LeadCard.model_validate_json(GOOD_CARD)
    assert card.priority == 4
    assert card.category is Category.NEW_LEAD


def test_optional_fields_can_be_null():
    raw = GOOD_CARD.replace('"company":"Acme"', '"company":null')
    assert LeadCard.model_validate_json(raw).company is None


@pytest.mark.parametrize(
    "bad",
    [
        BAD_PRIORITY,
        GOOD_CARD.replace('"priority":4', '"priority":"very high"'),
        GOOD_CARD.replace("raj@acme.com", "raj at acme"),
        GOOD_CARD.replace("new_lead", "hot"),
        GOOD_CARD.replace('"confidence":0.9', '"confidence":1.5'),
        GOOD_CARD.replace('"category":"new_lead",', ""),  # missing required field
        "not json at all",
    ],
)
def test_invalid_cards_are_rejected(bad):
    with pytest.raises(ValidationError):
        LeadCard.model_validate_json(bad)
