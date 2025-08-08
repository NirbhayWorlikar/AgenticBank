from app.core.pipeline import AgentPipeline


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


def test_pipeline_transfer_one_turn():
    pipe = AgentPipeline()
    r = pipe.process("transfer 10 from 111111 to 222222")
    assert r.awaiting_user is False
    assert r.intent is not None
    assert any(m.role == 'assistant' for m in r.messages) 