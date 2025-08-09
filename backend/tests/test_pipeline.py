import pytest
from app.core.pipeline import AgentPipeline, USE_LLM


@pytest.mark.skipif(USE_LLM, reason="Skip rule-based pipeline test in LLM mode")
def test_pipeline_card_replace_clarification_then_complete(monkeypatch):
    pipe = AgentPipeline()

    # First turn: missing slots prompt
    r1 = pipe.process("Please replace my card")
    assert r1.awaiting_user is True
    assert r1.intent is not None
    assert len(r1.missing_slots) > 0

    # Provide missing info
    r2 = pipe.process("credit, ship to 123 Main St, it's lost", session_id=r1.session_id)
    assert r2.awaiting_user is False
    assert r2.intent == r1.intent
    assert any(m.role == 'assistant' for m in r2.messages)


@pytest.mark.skipif(USE_LLM, reason="Skip rule-based pipeline test in LLM mode")
def test_pipeline_transfer_one_turn():
    pipe = AgentPipeline()
    r = pipe.process("transfer 10 from 111111 to 222222")
    assert r.awaiting_user is False
    assert r.intent is not None
    assert any(m.role == 'assistant' for m in r.messages)


def test_pipeline_llm_fallback_on_invalid_intent(monkeypatch):
    from app.core.pipeline import AgentPipeline, USE_LLM
    if not USE_LLM:
        return  # Only run for LLM mode
    pipe = AgentPipeline()
    # Patch planner to return no intent
    class DummyPlanner:
        def run(self, msg):
            from app.core.types import Plan
            return Plan(intent=None, slots={}, missing_slots=[], rationale="")
    monkeypatch.setattr(pipe, '_get_agents', lambda logger: (DummyPlanner(), None, None, None, lambda user, reason: f"FB: {reason}"))
    r = pipe.process("gibberish not a bank query")
    assert any("FB:" in m.content for m in r.messages if hasattr(m, 'content'))

def test_pipeline_llm_fallback_on_plan_review(monkeypatch):
    from app.core.pipeline import AgentPipeline, USE_LLM
    if not USE_LLM:
        return
    pipe = AgentPipeline()
    class DummyPlanner:
        def run(self, msg):
            from app.core.types import Plan
            return Plan(intent="card_replace", slots={}, missing_slots=[], rationale="")
    class DummyReviewer:
        def review_plan(self, plan):
            class R: approval = False; score = 0.0
            return R()
        def review_execution(self, plan, exec_result):
            class R: approval = True; score = 1.0
            return R()
    monkeypatch.setattr(pipe, '_get_agents', lambda logger: (DummyPlanner(), DummyReviewer(), None, None, lambda user, reason: f"FB: {reason}"))
    r = pipe.process("replace my card")
    assert any("FB:" in m.content for m in r.messages if hasattr(m, 'content'))

def test_pipeline_llm_fallback_on_execution_fail(monkeypatch):
    from app.core.pipeline import AgentPipeline, USE_LLM
    if not USE_LLM:
        return
    pipe = AgentPipeline()
    class DummyPlanner:
        def run(self, msg):
            from app.core.types import Plan
            return Plan(intent="card_replace", slots={}, missing_slots=[], rationale="")
    class DummyReviewer:
        def review_plan(self, plan):
            class R: approval = True; score = 1.0
            return R()
        def review_execution(self, plan, exec_result):
            class R: approval = True; score = 1.0
            return R()
    def fail_exec(plan):
        from app.core.types import ExecutionResult
        return ExecutionResult(success=False, data={}, error="fail")
    monkeypatch.setattr(pipe, '_get_agents', lambda logger: (DummyPlanner(), DummyReviewer(), fail_exec, None, lambda user, reason: f"FB: {reason}"))
    r = pipe.process("replace my card")
    assert any("FB:" in m.content for m in r.messages if hasattr(m, 'content'))

def test_pipeline_llm_clarification(monkeypatch):
    from app.core.pipeline import AgentPipeline, USE_LLM
    if not USE_LLM:
        return
    pipe = AgentPipeline()

    # Stateful planner that fills required slots across turns based on user message
    class DummyPlanner:
        def __init__(self):
            self.known_slots = {"card_type": None, "delivery_address": None, "reason": None}
        def run(self, msg):
            from app.core.types import Plan
            m = msg.lower()
            if "credit" in m or "debit" in m:
                self.known_slots["card_type"] = "credit" if "credit" in m else "debit"
            if "ship to" in m or "address" in m or "st" in m:
                self.known_slots["delivery_address"] = "123 main st" if "123" in m else self.known_slots["delivery_address"]
            if "lost" in m or "stolen" in m or "damaged" in m:
                if "lost" in m:
                    self.known_slots["reason"] = "lost"
                elif "stolen" in m:
                    self.known_slots["reason"] = "stolen"
                else:
                    self.known_slots["reason"] = "damaged"
            slots = {k: v for k, v in self.known_slots.items() if v is not None}
            required = ["card_type", "delivery_address", "reason"]
            missing = [k for k in required if k not in slots]
            return Plan(intent="card_replace", slots=slots, missing_slots=missing, rationale="")

    class DummyReviewer:
        def review_plan(self, plan):
            class R: approval = True; score = 1.0
            return R()
        def review_execution(self, plan, exec_result):
            class R: approval = True; score = 1.0
            return R()

    def exec_ok(plan):
        from app.core.types import ExecutionResult
        return ExecutionResult(success=True, data={"ok": True}, error=None)
    def responder(exec_result):
        return "All done!"
    def fallback(user, reason):
        return f"FB: {reason}"

    monkeypatch.setattr(pipe, '_get_agents', lambda logger: (DummyPlanner(), DummyReviewer(), exec_ok, responder, fallback))

    # Turn 1: no slots
    r1 = pipe.process("replace my card")
    assert r1.awaiting_user is True
    assert set(r1.missing_slots) >= {"card_type", "delivery_address", "reason"}

    # Turn 2: provide card type
    r2 = pipe.process("credit", session_id=r1.session_id)
    assert r2.awaiting_user is True

    # Turn 3: provide address
    r3 = pipe.process("ship to 123 Main St", session_id=r1.session_id)
    assert r3.awaiting_user is True

    # Turn 4: provide reason -> should execute and finish
    r4 = pipe.process("it's lost", session_id=r1.session_id)
    assert r4.awaiting_user is False
    assert any("All done!" in m.content for m in r4.messages if hasattr(m, 'content')) 