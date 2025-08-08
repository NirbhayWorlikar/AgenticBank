from __future__ import annotations

import json
from typing import Dict, List, Optional

from app.core.logger import SessionLogger
from app.core.types import INTENT_TO_REQUIRED_SLOTS, IntentName, Plan
from app.llm.bedrock import call_llm_json, get_bedrock_client


PLANNER_PROMPT = (
    "You extract user intent and required slots for a banking assistant.\n"
    "Supported intents: card_replace, report_fraud, open_account, check_balance, transfer_money.\n"
    "Return a compact JSON: {intent: string|null, slots: object}.\n"
    "Only use keys from the required slots for the intent. If uncertain, set intent to null.\n"
)


class LLMPlanner:
    def __init__(self, logger: SessionLogger) -> None:
        self.logger = logger
        self.llm = get_bedrock_client()

    def run(self, user_message: str) -> Plan:
        prompt = PLANNER_PROMPT + f"\nUser: {user_message}\nJSON:"
        raw = call_llm_json(self.llm, prompt)
        intent: Optional[IntentName] = None
        slots: Dict[str, Optional[str]] = {}
        try:
            data = json.loads(raw)
            if isinstance(data.get("intent"), str) and data["intent"] in [i.value for i in IntentName]:
                intent = IntentName(data["intent"]) 
            slots = data.get("slots", {}) or {}
        except Exception:
            # fall back to no-intent plan
            pass

        missing: List[str] = []
        if intent:
            required = INTENT_TO_REQUIRED_SLOTS[intent]
            # keep only required keys
            slots = {k: (slots.get(k) if slots.get(k) else None) for k in required}
            missing = [k for k in required if not slots.get(k)]

        plan = Plan(intent=intent, slots=slots, missing_slots=missing, rationale="LLM extracted plan")
        self.logger.step("planner_llm", {"user_message": user_message}, plan.model_dump())
        return plan 