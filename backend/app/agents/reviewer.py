from __future__ import annotations

from typing import List, Optional

from app.core.logger import SessionLogger
from app.core.types import INTENT_TO_REQUIRED_SLOTS, ExecutionResult, Plan, Review, ReviewType


class Reviewer:
    def __init__(self, logger: SessionLogger) -> None:
        self.logger = logger

    def review_plan(self, plan: Plan) -> Review:
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

        review = Review(approved=approved, issues=issues, score=round(score, 2), review_type=ReviewType.plan)
        self.logger.step("reviewer", {"review_type": "plan", "plan": plan.model_dump()}, review.model_dump())
        return review

    def review_execution(self, plan: Plan, exec_result: ExecutionResult) -> Review:
        issues: List[str] = []
        score = 0.7 if exec_result.success else 0.2

        if not exec_result.success:
            issues.append(exec_result.error or "Execution failed for unknown reason")
        else:
            # Simple sanity checks per intent (PoC level)
            if plan.intent is not None:
                if plan.intent.value == "transfer_money":
                    if not exec_result.data.get("transfer_id"):
                        issues.append("Missing transfer_id in execution result")
                if plan.intent.value == "check_balance":
                    if "balance" not in exec_result.data:
                        issues.append("Missing balance in execution result")

        approved = len(issues) == 0 and exec_result.success
        review = Review(approved=approved, issues=issues, score=round(score, 2), review_type=ReviewType.execution)
        self.logger.step(
            "reviewer",
            {"review_type": "execution", "plan": plan.model_dump(), "result": exec_result.model_dump()},
            review.model_dump(),
        )
        return review 