import pytest

from app.core.pipeline import AgentPipeline, USE_LLM


@pytest.mark.skipif(not USE_LLM, reason="Requires LLM mode")
def test_llm_mode_clarification_prompts_and_completes(monkeypatch):
    pipe = AgentPipeline()

    # Planner that returns card_replace with missing slots initially; then merges
    class DummyPlanner:
        def __init__(self):
            self.slots = {"card_type": None, "delivery_address": None, "reason": None}
        def run(self, msg):
            from app.core.types import Plan
            m = msg.lower()
            if "credit" in m or "debit" in m:
                self.slots["card_type"] = "credit" if "credit" in m else "debit"
            if "ship to" in m or "address" in m or "st" in m:
                self.slots["delivery_address"] = "123 main st" if "123" in m else (self.slots["delivery_address"] or "456 oak ave")
            if "lost" in m or "stolen" in m or "damaged" in m:
                self.slots["reason"] = "lost" if "lost" in m else ("stolen" if "stolen" in m else "damaged")
            present = {k: v for k, v in self.slots.items() if v}
            required = ["card_type", "delivery_address", "reason"]
            missing = [k for k in required if k not in present]
            return Plan(intent="card_replace", slots=present, missing_slots=missing, rationale="")

    class DummyReviewer:
        def review_plan(self, plan):
            class R: approved = True; score = 10
            return R()
        def review_execution(self, plan, exec_result):
            class R: approved = True; score = 10
            return R()

    def exec_ok(plan):
        from app.core.types import ExecutionResult
        return ExecutionResult(success=True, data={"ok": True})

    def responder(exec_result):
        return "All done!"

    def fallback(user, reason):
        return f"FB: {reason}"

    monkeypatch.setattr(pipe, '_get_agents', lambda logger: (DummyPlanner(), DummyReviewer(), exec_ok, responder, fallback))

    # Turn 1: should prompt for missing slots (no plan exposure)
    r1 = pipe.process("replace my card")
    assert r1.awaiting_user is True
    assistant_msgs = [m.content for m in r1.messages if getattr(m, 'role', None) == 'assistant']
    assert assistant_msgs, "Assistant clarification message missing"
    assert not any("```json" in msg or '"intent"' in msg for msg in assistant_msgs)
    assert any("card_type" in msg and "delivery_address" in msg and "reason" in msg for msg in assistant_msgs)

    # Turn 2: provide partial info (card_type)
    r2 = pipe.process("credit", session_id=r1.session_id)
    assert r2.awaiting_user is True

    # Turn 3: provide address
    r3 = pipe.process("ship to 123 Main St", session_id=r1.session_id)
    assert r3.awaiting_user is True

    # Turn 4: provide reason and complete
    r4 = pipe.process("it's lost", session_id=r1.session_id)
    assert r4.awaiting_user is False
    assert any(getattr(m, 'role', None) == 'assistant' for m in r4.messages) 