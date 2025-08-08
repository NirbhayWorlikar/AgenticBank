from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

from .types import INTENT_TO_REQUIRED_SLOTS, IntentName


def detect_intent(text: str) -> Optional[IntentName]:
    t = text.lower()

    # Card replacement: match lost/stolen/damaged + card, or replace + card
    if re.search(r"(lost|stolen|damaged)[^\n]{0,40}\bcard\b", t) or re.search(
        r"\breplace[^\n]{0,40}\b(card|debit|credit)\b", t
    ) or (re.search(r"\b(lost|stolen|damaged)\b", t) and re.search(r"\b(card|debit|credit)\b", t)):
        return IntentName.card_replace

    # Fraud report
    if re.search(r"\b(fraud|unauthori[sz]ed|dispute)\b", t):
        return IntentName.report_fraud

    # Open account
    if re.search(r"\b(open|create)\b[^\n]{0,30}\b(account)\b", t):
        return IntentName.open_account

    # Check balance
    if re.search(r"\b(balance|funds available|how much do i have)\b", t):
        return IntentName.check_balance

    # Transfer money
    if re.search(r"\b(transfer|send|pay)\b[^\n]{0,30}\b(money|amount|\$|to|from|[0-9])\b", t):
        return IntentName.transfer_money

    return None


def extract_slots(intent: Optional[IntentName], text: str) -> Tuple[Dict[str, Optional[str]], List[str]]:
    if intent is None:
        return {}, []

    required = INTENT_TO_REQUIRED_SLOTS[intent]
    slots: Dict[str, Optional[str]] = {s: None for s in required}

    # Very naive regex/pattern based extraction just for PoC
    t = text

    if intent == IntentName.card_replace:
        # Only set when explicitly stated and not just as part of 'credit card'
        m = re.search(r"(card type|type of card)[:\s]*(debit|credit)", t, re.I)
        if not m:
            m = re.search(r"\b(debit|credit)\b(?!\s*card)", t, re.I)
        if m:
            slots["card_type"] = m.group(2) if m.lastindex and m.lastindex >= 2 else m.group(1)
            if slots["card_type"] not in ("debit", "credit"):
                slots["card_type"] = None

        m = re.search(r"address is ([^.\n]+)", t, re.I)
        if m:
            slots["delivery_address"] = m.group(1).strip()
        m = re.search(r"ship to ([^.\n]+)", t, re.I)
        if m:
            slots["delivery_address"] = m.group(1).strip()
        if re.search(r"lost|stolen|damaged", t, re.I):
            slots["reason"] = re.search(r"lost|stolen|damaged", t, re.I).group(0)

    elif intent == IntentName.report_fraud:
        m = re.search(r"transaction(?: id)?[:\s]*([A-Za-z0-9-]{6,})", t, re.I)
        if m:
            slots["transaction_id"] = m.group(1)
        if re.search(r"card|upi|netbank|ach|wire", t, re.I):
            slots["fraud_type"] = re.search(r"card|upi|netbank|ach|wire", t, re.I).group(0)
        if re.search(r"\b(confirm|yes|proceed)\b", t, re.I):
            slots["user_confirmation"] = "yes"

    elif intent == IntentName.open_account:
        if re.search(r"savings|checking|current", t, re.I):
            slots["account_type"] = re.search(r"savings|checking|current", t, re.I).group(0)
        m = re.search(r"name is ([A-Za-z ]{3,})", t, re.I)
        if m:
            slots["customer_name"] = m.group(1).strip()
        m = re.search(r"id(?:\s*proof)?[:\s]*([A-Za-z0-9-]{4,})", t, re.I)
        if m:
            slots["id_proof"] = m.group(1)

    elif intent == IntentName.check_balance:
        m = re.search(r"account(?: number| no\.)?[:\s]*([0-9]{6,})", t, re.I)
        if m:
            slots["account_number"] = m.group(1)
        m = re.search(r"(token|auth|otp)[:\s]*([A-Za-z0-9-]{4,})", t, re.I)
        if m:
            slots["auth_token"] = m.group(2)

    elif intent == IntentName.transfer_money:
        m = re.search(r"from[:\s]*([0-9]{6,})", t, re.I)
        if m:
            slots["sender_account"] = m.group(1)
        m = re.search(r"to[:\s]*([0-9]{6,})", t, re.I)
        if m:
            slots["receiver_account"] = m.group(1)
        m = re.search(r"amount[:\s]*\$?([0-9]+(?:\.[0-9]{1,2})?)", t, re.I)
        if m:
            slots["amount"] = m.group(1)
        # Fallback: handle 'transfer 10' or 'send 10'
        if not slots.get("amount"):
            m = re.search(r"\b(?:transfer|send|pay)\s+\$?([0-9]+(?:\.[0-9]{1,2})?)\b", t, re.I)
            if m:
                slots["amount"] = m.group(1)

    missing = [k for k, v in slots.items() if not v]
    return slots, missing 