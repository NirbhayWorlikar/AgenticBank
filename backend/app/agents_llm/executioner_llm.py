from __future__ import annotations

import random
from typing import Dict, Any

from app.llm.bedrock import call_llm_json, get_bedrock_client
from app.core.types import Plan, ExecutionResult


def execute_plan_llm(plan: Plan) -> ExecutionResult:
    # Simulate agent/tool availability (80% available)
    available = random.random() < 0.8
    if not available:
        return ExecutionResult(success=False, data={}, error="Agent/tool unavailable. Please try again later.")

    # Ask LLM to simulate execution; fall back to deterministic mock
    llm = get_bedrock_client()
    prompt = f"""
You are a banking execution agent. Given this plan, simulate the banking action and return a detailed JSON result. If the plan is invalid, return an error.
Plan: {plan.model_dump_json()}
Respond in JSON with keys: success (bool), data (object), error (string or null).
"""
    parsed = call_llm_json(prompt, llm)

    if isinstance(parsed, dict):
        success = bool(parsed.get("success", True))
        data = parsed.get("data", {}) if isinstance(parsed.get("data", {}), dict) else {}
        error = parsed.get("error")
        return ExecutionResult(success=success, data=data, error=error)

    # Fallback deterministic simulation
    intent = plan.intent.value if plan.intent else "unknown"
    mock_data: Dict[str, Any] = {"intent": intent, **plan.slots}
    return ExecutionResult(success=True, data=mock_data, error=None) 