import pytest

from app.core.pipeline import AgentPipeline, USE_LLM


@pytest.mark.skipif(not USE_LLM, reason="Requires LLM mode")
def test_llm_scores_present_for_clarification_and_completion(monkeypatch):
    pipe = AgentPipeline()

    # Planner that fills required slots across turns
    class DummyPlanner:
        def __init__(self):
            self.known = {"card_type": None, "delivery_address": None, "reason": None}
        def run(self, msg):
            from app.core.types import Plan
            m = msg.lower()
            if "credit" in m or "debit" in m:
                self.known["card_type"] = "credit" if "credit" in m else "debit"
            if "ship to" in m or "address" in m or "st" in m:
                self.known["delivery_address"] = "123 main st"
            if any(k in m for k in ["lost", "stolen", "damaged"]):
                self.known["reason"] = "lost" if "lost" in m else ("stolen" if "stolen" in m else "damaged")
            slots = {k: v for k, v in self.known.items() if v is not None}
            required = ["card_type", "delivery_address", "reason"]
            missing = [k for k in required if k not in slots]
            return Plan(intent="card_replace", slots=slots, missing_slots=missing, rationale="")

    class DummyReviewer:
        def review_plan(self, plan):
            class R: approved = True; score = 8.5
            return R()
        def review_execution(self, plan, exec_result):
            class R: approved = True; score = 9.0
            return R()

    def exec_ok(plan):
        from app.core.types import ExecutionResult
        return ExecutionResult(success=True, data={"ok": True})

    def responder(exec_result):
        return "All done!"

    def fallback(user, reason):
        return f"FB: {reason}"

    monkeypatch.setattr(pipe, '_get_agents', lambda logger: (DummyPlanner(), DummyReviewer(), exec_ok, responder, fallback))

    # Turn 1: Should ask for clarifications and include plan_review_score only
    r1 = pipe.process("replace my card")
    assert r1.awaiting_user is True
    assert isinstance(r1.plan_review_score, (int, float)) and r1.plan_review_score > 0
    assert r1.execution_review_score is None

    # Turn 2: provide card_type
    r2 = pipe.process("credit", session_id=r1.session_id)
    assert r2.awaiting_user is True

    # Turn 3: provide address
    r3 = pipe.process("ship to 123 main st", session_id=r1.session_id)
    assert r3.awaiting_user is True

    # Turn 4: provide reason -> complete
    r4 = pipe.process("it's lost", session_id=r1.session_id)
    assert r4.awaiting_user is False
    assert isinstance(r4.plan_review_score, (int, float)) and r4.plan_review_score > 0
    assert isinstance(r4.execution_review_score, (int, float)) and r4.execution_review_score > 0 