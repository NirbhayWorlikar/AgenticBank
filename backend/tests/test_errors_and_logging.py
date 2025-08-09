import os
from pathlib import Path
from typing import Optional

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.pipeline import AgentPipeline, USE_LLM


client = TestClient(app)


@pytest.mark.skipif(USE_LLM, reason="These tests target rule-based mode")
def test_api_invalid_payload_returns_422():
    r = client.post("/chat", json={})
    assert r.status_code == 422


@pytest.mark.skipif(USE_LLM, reason="These tests target rule-based mode")
def test_cancel_resets_session_and_prompts_again():
    pipe = AgentPipeline()
    # Start a session needing clarification
    r1 = pipe.process("Please replace my card")
    assert r1.awaiting_user is True
    sid = r1.session_id
    # Send cancel
    r2 = pipe.process("cancel", session_id=sid)
    assert r2.awaiting_user is True
    assert r2.state == "idle" or (hasattr(r2.state, 'value') and r2.state.value == 'idle')
    # After cancel, a new query should create a fresh plan
    r3 = pipe.process("transfer 10 from 111111 to 222222", session_id=sid)
    assert r3.awaiting_user is False


@pytest.mark.skipif(USE_LLM, reason="These tests target rule-based mode")
def test_clarification_message_mentions_missing_slots_without_plan_exposure():
    pipe = AgentPipeline()
    r1 = pipe.process("Please replace my card")
    assert r1.awaiting_user is True
    # Assistant message should NOT include a code block or plan JSON
    assistant_msgs = [m.content for m in r1.messages if getattr(m, 'role', None) == 'assistant']
    assert not any("```json" in msg or '"intent"' in msg for msg in assistant_msgs)
    # Should list missing slot names in a friendly way
    assert any("card_type" in msg and "delivery_address" in msg and "reason" in msg for msg in assistant_msgs)


@pytest.mark.skipif(USE_LLM, reason="These tests target rule-based mode")
def test_logs_are_written_per_session(tmp_path, monkeypatch):
    # Point logger to a temp directory to avoid polluting repo logs
    temp_logs_dir = tmp_path / "logs"
    temp_logs_dir.mkdir(parents=True, exist_ok=True)

    # Monkeypatch SessionLogger used by pipeline to use temp base_dir
    import app.core.pipeline as pipeline_mod

    class TempSessionLogger(pipeline_mod.SessionLogger):
        def __init__(self, session_id: str, base_dir: Optional[str] = None) -> None:
            super().__init__(session_id, base_dir=str(temp_logs_dir))

    monkeypatch.setattr(pipeline_mod, 'SessionLogger', TempSessionLogger)

    pipe = AgentPipeline()
    r = pipe.process("Please replace my card")
    sid = r.session_id

    log_file = temp_logs_dir / f"session_{sid}.jsonl"
    assert log_file.exists()
    content = log_file.read_text(encoding="utf-8").strip().splitlines()
    assert any('\"event\": \"user_message\"' in line for line in content)
    assert any('\"event\": \"agent_step\"' in line for line in content) 