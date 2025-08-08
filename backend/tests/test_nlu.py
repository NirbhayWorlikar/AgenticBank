from app.core.nlu import detect_intent, extract_slots
from app.core.types import IntentName


def test_detect_intent_card_replace():
    text = "I lost my credit card, please replace it"
    intent = detect_intent(text)
    assert intent == IntentName.card_replace


def test_extract_slots_card_replace():
    text = "I lost my credit card. address is 123 Main St"
    intent = IntentName.card_replace
    slots, missing = extract_slots(intent, text)
    assert slots["delivery_address"] == "123 Main St"
    assert slots["reason"] == "lost"
    assert "card_type" in missing  # not specified


def test_detect_intent_transfer():
    text = "transfer 25 from 111111 to 222222"
    intent = detect_intent(text)
    assert intent == IntentName.transfer_money


def test_extract_slots_transfer():
    text = "transfer amount 25 from 111111 to 222222"
    intent = IntentName.transfer_money
    slots, missing = extract_slots(intent, text)
    assert slots["sender_account"] == "111111"
    assert slots["receiver_account"] == "222222"
    assert slots["amount"] == "25" 