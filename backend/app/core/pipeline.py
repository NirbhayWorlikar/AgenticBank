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
            return LLMPlanner(logger), LLMReviewer(logger), Executioner(logger), Responder(logger)
        return Planner(logger), Reviewer(logger), Executioner(logger), Responder(logger)

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
                    Message(role="assistant", content="Okay, I’ve reset this conversation. How can I help next?"),
                ],
                awaiting_user=True,
                missing_slots=[],
                intent=None,
                state=SessionState.idle,
            )

        if self._is_new_request(user_message):
            self._memory[sid] = SessionMemory(state=SessionState.idle, plan=None)
            logger.info("New request command recognized; state reset")

        planner, reviewer, executioner, responder = self._get_agents(logger)

        if mem.state in (SessionState.awaiting_clarification,) and mem.plan:
            incoming_plan: Plan = planner.run(user_message)
            # If user replied with only slot values (no intent), extract based on previous intent
            if not incoming_plan.intent and mem.plan.intent:
                slots, missing = extract_slots(mem.plan.intent, user_message)
                incoming_plan = Plan(intent=mem.plan.intent, slots=slots, missing_slots=missing, rationale=incoming_plan.rationale)
            plan: Plan = self._merge_with_memory(mem.plan, incoming_plan)
        else:
            plan = planner.run(user_message)

        plan_review = reviewer.review_plan(plan)

        if plan.intent and plan.missing_slots:
            self._set_state(logger, mem, SessionState.awaiting_clarification)
            mem.plan = plan
            assistant_msg = responder.run(plan, result=None)
            logger.assistant_message(assistant_msg.content)
            return ChatResponse(
                session_id=sid,
                messages=[Message(role="user", content=user_message), assistant_msg],
                awaiting_user=True,
                missing_slots=plan.missing_slots,
                intent=plan.intent,
                state=mem.state,
            )

        self._set_state(logger, mem, SessionState.executing)
        exec_result = executioner.run(plan)

        execution_review = reviewer.review_execution(plan, exec_result)

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
        ) 