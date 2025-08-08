from __future__ import annotations

from typing import List

from app.core.logger import SessionLogger
from app.core.types import INTENT_TO_REQUIRED_SLOTS, Plan, Review


class Reviewer:
    def __init__(self, logger: SessionLogger) -> None:
        self.logger = logger

    def run(self, plan: Plan) -> Review:
        issues: List[str] = []
        score = 0.5

        if plan.intent is None:
            issues.append("No intent detected")
        else:
            required = set(INTENT_TO_REQUIRED_SLOTS[plan.intent])
            provided = set(plan.slots.keys())
            if not required.issubset(provided):
                issues.append("Slots keys don't match required set")
            missing = [k for k in required if not plan.slots.get(k)]
            if missing:
                issues.append(f"Missing required slots: {', '.join(missing)}")
            score = 0.6 + 0.4 * (1.0 - len(missing) / max(1, len(required)))

        approved = len(issues) == 0 or (len(issues) == 1 and "Missing required slots" in issues[0])

        review = Review(approved=approved, issues=issues, score=round(score, 2))
        self.logger.step("reviewer", {"plan": plan.model_dump()}, review.model_dump())
        return review 