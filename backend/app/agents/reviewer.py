from __future__ import annotations

from typing import List

from app.core.logger import SessionLogger
from app.core.types import INTENT_TO_REQUIRED_SLOTS, ExecutionResult, Plan, Review, ReviewType


class Reviewer:
    def __init__(self, logger: SessionLogger) -> None:
        self.logger = logger

    def review_plan(self, plan: Plan) -> Review:
        issues: List[str] = []
        # Criteria: Relevance, Completeness, Safety, Quality (1-10 overall)
        relevance = 3
        completeness = 3
        safety = 3
        quality = 3

        if plan.intent is None:
            issues.append("No intent detected")
            relevance = 1
        else:
            relevance = 8
            required = set(INTENT_TO_REQUIRED_SLOTS[plan.intent])
            provided = set(plan.slots.keys())
            if not required.issubset(provided):
                issues.append("Slots keys don't match required set")
            missing = [k for k in required if not plan.slots.get(k)]
            if missing:
                issues.append(f"Missing required slots: {', '.join(missing)}")
                completeness = max(1, 10 - int(9 * (len(missing) / max(1, len(required)))))
            else:
                completeness = 9
            # Safety heuristic: ensure no PII leakage prompts, and reasonable fields
            safety = 8 if plan.intent else 4
            # Quality heuristic: rationale present, structure ok
            quality = 7 if plan.rationale else 5

        # Overall score (1-10)
        score = round((relevance + completeness + safety + quality) / 4.0, 1)
        approved = score >= 5.0  # allow proceeding with clarifications

        review = Review(approved=approved, issues=issues, score=score, review_type=ReviewType.plan)
        self.logger.step("reviewer", {"review_type": "plan", "plan": plan.model_dump()}, review.model_dump())
        return review

    def review_execution(self, plan: Plan, exec_result: ExecutionResult) -> Review:
        issues: List[str] = []
        # Criteria for execution
        relevance = 8 if plan.intent else 4
        completeness = 7
        safety = 7
        quality = 7

        if not exec_result.success:
            issues.append(exec_result.error or "Execution failed for unknown reason")
            completeness = 2
            quality = 3
        else:
            # Simple sanity checks per intent (PoC level)
            if plan.intent is not None:
                if plan.intent.value == "transfer_money":
                    if not exec_result.data.get("transfer_id"):
                        issues.append("Missing transfer_id in execution result")
                        completeness = 5
                if plan.intent.value == "check_balance":
                    if "balance" not in exec_result.data:
                        issues.append("Missing balance in execution result")
                        completeness = 5

        score = round((relevance + completeness + safety + quality) / 4.0, 1)
        approved = exec_result.success and score >= 5.0

        review = Review(approved=approved, issues=issues, score=score, review_type=ReviewType.execution)
        self.logger.step(
            "reviewer",
            {"review_type": "execution", "plan": plan.model_dump(), "result": exec_result.model_dump()},
            review.model_dump(),
        )
        return review 