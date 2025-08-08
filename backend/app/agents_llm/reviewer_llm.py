from __future__ import annotations

import json
from typing import List

from app.core.logger import SessionLogger
from app.core.types import ExecutionResult, Plan, Review, ReviewType
from app.llm.bedrock import call_llm_json, get_bedrock_client


REVIEW_PLAN_PROMPT = (
    "You review a plan for intent and completeness.\n"
    "Return JSON: {approved: boolean, issues: string[], score: number}.\n"
)

REVIEW_EXEC_PROMPT = (
    "You review an execution result for sanity and user safety.\n"
    "Return JSON: {approved: boolean, issues: string[], score: number}.\n"
)


class LLMReviewer:
    def __init__(self, logger: SessionLogger) -> None:
        self.logger = logger
        self.llm = get_bedrock_client()

    def review_plan(self, plan: Plan) -> Review:
        prompt = REVIEW_PLAN_PROMPT + f"\nPlan: {plan.model_dump_json()}\nJSON:"
        raw = call_llm_json(self.llm, prompt)
        issues: List[str] = []
        approved = True
        score = 0.7
        try:
            data = json.loads(raw)
            approved = bool(data.get("approved", True))
            issues = list(data.get("issues", []))
            score = float(data.get("score", 0.7))
        except Exception:
            pass
        review = Review(approved=approved, issues=issues, score=round(score, 2), review_type=ReviewType.plan)
        self.logger.step("reviewer_llm", {"type": "plan", "plan": plan.model_dump()}, review.model_dump())
        return review

    def review_execution(self, plan: Plan, result: ExecutionResult) -> Review:
        prompt = REVIEW_EXEC_PROMPT + f"\nPlan: {plan.model_dump_json()}\nResult: {result.model_dump_json()}\nJSON:"
        raw = call_llm_json(self.llm, prompt)
        issues: List[str] = []
        approved = bool(result.success)
        score = 0.7 if result.success else 0.2
        try:
            data = json.loads(raw)
            approved = bool(data.get("approved", approved))
            issues = list(data.get("issues", []))
            score = float(data.get("score", score))
        except Exception:
            pass
        review = Review(approved=approved, issues=issues, score=round(score, 2), review_type=ReviewType.execution)
        self.logger.step(
            "reviewer_llm",
            {"type": "execution", "plan": plan.model_dump(), "result": result.model_dump()},
            review.model_dump(),
        )
        return review 