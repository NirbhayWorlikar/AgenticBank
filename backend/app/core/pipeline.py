from __future__ import annotations

import os
import re
import uuid
from dataclasses import dataclass
from typing import Dict, Optional

from app.agents.executioner import Executioner
from app.agents.planner import Planner
from app.agents.responder import Responder
from app.agents.reviewer import Reviewer
from app.agents_llm.planner_llm import LLMPlanner
from app.agents_llm.reviewer_llm import LLMReviewer
from app.agents_llm.executioner_llm import execute_plan_llm
from app.agents_llm.responder_llm import summarize_result_llm
from app.agents_llm.fallback_agent_llm import fallback_response_llm
from app.core.logger import SessionLogger
from app.core.types import (
    ChatResponse,
    INTENT_TO_REQUIRED_SLOTS,
    IntentName,
    Message,
    Plan,
    SessionState,
)
from app.core.nlu import extract_slots


USE_LLM = os.getenv("USE_LLM", "false").lower() in {"1", "true", "yes"}


@dataclass
class SessionMemory:
    state: SessionState
    plan: Optional[Plan]


class AgentPipeline:
    def __init__(self) -> None:
        self._loggers: dict[str, SessionLogger] = {}
        self._memory: Dict[str, SessionMemory] = {}

    def _get_logger(self, session_id: str) -> SessionLogger:
        if session_id not in self._loggers:
            self._loggers[session_id] = SessionLogger(session_id)
        return self._loggers[session_id]

    def _get_memory(self, session_id: str) -> SessionMemory:
        mem = self._memory.get(session_id)
        if not mem:
            mem = SessionMemory(state=SessionState.idle, plan=None)
            self._memory[session_id] = mem
        return mem

    def _set_state(self, logger: SessionLogger, mem: SessionMemory, new_state: SessionState) -> None:
        if mem.state != new_state:
            logger.state_transition(mem.state.value, new_state.value)
            mem.state = new_state

    def _is_cancel(self, text: str) -> bool:
        return bool(re.search(r"\b(cancel|stop|never mind|reset|start over)\b", text, re.I))

    def _is_new_request(self, text: str) -> bool:
        return bool(re.search(r"\b(new (request|issue|intent)|different (request|issue))\b", text, re.I))

    def _merge_with_memory(self, existing: Plan, incoming: Plan) -> Plan:
        intent = existing.intent or incoming.intent
        if not intent:
            return incoming

        required = INTENT_TO_REQUIRED_SLOTS[intent]
        merged_slots: Dict[str, str | None] = {s: None for s in required}

        for k in required:
            if existing.slots.get(k):
                merged_slots[k] = existing.slots[k]
        for k in required:
            if incoming.slots.get(k):
                merged_slots[k] = incoming.slots[k]

        missing = [k for k in required if not merged_slots.get(k)]
        return Plan(intent=intent, slots=merged_slots, missing_slots=missing, rationale=incoming.rationale)

    def _get_agents(self, logger: SessionLogger):
        if USE_LLM:
            return LLMPlanner(logger), LLMReviewer(logger), execute_plan_llm, summarize_result_llm, fallback_response_llm
        return Planner(logger), Reviewer(logger), Executioner(logger), Responder(logger), None

    def _normalize_review(self, review_obj) -> tuple[bool, float]:
        """Return (approved, score_1_to_10) handling both 'approved' and legacy 'approval',
        and normalizing score if provided on 0-1 scale."""
        approved = bool(getattr(review_obj, "approved", None))
        if not approved and hasattr(review_obj, "approval"):
            approved = bool(getattr(review_obj, "approval"))
        score = getattr(review_obj, "score", None)
        try:
            score_val = float(score) if score is not None else 7.0
        except Exception:
            score_val = 7.0
        # Normalize: if score seems on 0-1 scale, map to 1-10
        if score_val <= 1.0:
            score_val = round(score_val * 10.0, 1)
        return approved, score_val

    def process(self, user_message: str, session_id: str | None = None) -> ChatResponse:
        sid = session_id or str(uuid.uuid4())
        logger = self._get_logger(sid)
        logger.user_message(user_message)
        mem = self._get_memory(sid)

        if self._is_cancel(user_message):
            self._memory[sid] = SessionMemory(state=SessionState.idle, plan=None)
            logger.assistant_message("Okay, I’ve reset this conversation. How can I help next?")
            return ChatResponse(
                session_id=sid,
                messages=[
                    Message(role="user", content=user_message),
                    Message(role="assistant", content="Okay, I’ve reset this conversation. How can I help next?")
                ],
                awaiting_user=True,
                missing_slots=[],
                intent=None,
                state=SessionState.idle,
                plan_review_score=None,
                execution_review_score=None,
            )

        if self._is_new_request(user_message):
            self._memory[sid] = SessionMemory(state=SessionState.idle, plan=None)
            logger.info("New request command recognized; state reset")

        planner, reviewer, executioner, responder, fallback = self._get_agents(logger)

        # LLM fallback wrapper
        def do_fallback(reason: str):
            msg = fallback(user_message, reason) if fallback else "Sorry, we couldn't process your request."
            logger.assistant_message(msg)
            return ChatResponse(
                session_id=sid,
                messages=[Message(role="user", content=user_message), Message(role="assistant", content=msg)],
                awaiting_user=False,
                missing_slots=[],
                intent=None,
                state=SessionState.idle,
                plan_review_score=None,
                execution_review_score=None,
            )

        # Clarification loop
        if mem.state in (SessionState.awaiting_clarification,) and mem.plan:
            incoming_plan: Plan = planner.run(user_message)
            if not incoming_plan.intent and mem.plan.intent:
                slots, missing = extract_slots(mem.plan.intent, user_message)
                incoming_plan = Plan(intent=mem.plan.intent, slots=slots, missing_slots=missing, rationale=incoming_plan.rationale)
            plan: Plan = self._merge_with_memory(mem.plan, incoming_plan)
        else:
            plan = planner.run(user_message)

        # LLM: Validate plan (intent must be present)
        if USE_LLM and (not plan.intent):
            return do_fallback("Could not detect a valid banking intent.")

        plan_review = reviewer.review_plan(plan)
        # Normalize review across schemas and scales
        plan_approved, plan_score = self._normalize_review(plan_review)
        if USE_LLM and (not plan_approved or plan_score < 5.0):
            return do_fallback("Plan review failed or plan score too low.")

        if plan.intent and plan.missing_slots:
            self._set_state(logger, mem, SessionState.awaiting_clarification)
            mem.plan = plan
            # Generate a friendly clarification message without exposing the internal plan
            clarification_message = Responder(logger).run(plan, result=None)
            logger.assistant_message(clarification_message.content)
            return ChatResponse(
                session_id=sid,
                messages=[
                    Message(role="user", content=user_message),
                    clarification_message,
                ],
                awaiting_user=True,
                missing_slots=plan.missing_slots,
                intent=plan.intent,
                state=mem.state,
                plan_review_score=plan_score,
                execution_review_score=None,
            )

        self._set_state(logger, mem, SessionState.executing)
        if USE_LLM:
            exec_result = executioner(plan)
            if not exec_result.success:
                return do_fallback("Execution failed or agent/tool unavailable.")
        else:
            exec_result = executioner.run(plan)

        execution_review = reviewer.review_execution(plan, exec_result)
        exec_approved, exec_score = self._normalize_review(execution_review)
        if USE_LLM and (not exec_approved or exec_score < 5.0):
            return do_fallback("Execution review failed or score too low.")

        if USE_LLM:
            summary = responder(exec_result)
            logger.assistant_message(summary)
            self._set_state(logger, mem, SessionState.completed)
            mem.plan = None
            self._set_state(logger, mem, SessionState.idle)
            return ChatResponse(
                session_id=sid,
                messages=[Message(role="user", content=user_message), Message(role="assistant", content=summary)],
                awaiting_user=False,
                missing_slots=[],
                intent=plan.intent,
                state=mem.state,
                plan_review_score=plan_score,
                execution_review_score=exec_score,
            )
        else:
            assistant_msg = responder.run(plan, exec_result)
            logger.assistant_message(assistant_msg.content)
            self._set_state(logger, mem, SessionState.completed)
            mem.plan = None
            self._set_state(logger, mem, SessionState.idle)
            return ChatResponse(
                session_id=sid,
                messages=[Message(role="user", content=user_message), assistant_msg],
                awaiting_user=False,
                missing_slots=[],
                intent=plan.intent,
                state=mem.state,
                plan_review_score=plan_score,
                execution_review_score=exec_score,
            ) 