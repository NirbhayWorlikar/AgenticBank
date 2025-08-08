from __future__ import annotations

from typing import Dict

from app.core.logger import SessionLogger
from app.core.nlu import detect_intent, extract_slots
from app.core.types import Plan


class Planner:
    def __init__(self, logger: SessionLogger) -> None:
        self.logger = logger

    def run(self, user_message: str) -> Plan:
        intent = detect_intent(user_message)
        slots, missing = extract_slots(intent, user_message)
        plan = Plan(
            intent=intent,
            slots=slots,
            missing_slots=missing,
            rationale="Derived via rule-based NLU for PoC.",
        )
        self.logger.step(
            "planner",
            {"user_message": user_message},
            plan.model_dump(),
        )
        return plan 