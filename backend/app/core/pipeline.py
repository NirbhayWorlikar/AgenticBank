from __future__ import annotations

import uuid
from typing import Dict

from app.agents.executioner import Executioner
from app.agents.planner import Planner
from app.agents.responder import Responder
from app.agents.reviewer import Reviewer
from app.core.logger import SessionLogger
from app.core.types import ChatResponse, INTENT_TO_REQUIRED_SLOTS, IntentName, Message, Plan


class AgentPipeline:
    def __init__(self) -> None:
        self._loggers: dict[str, SessionLogger] = {}
        # Memory of ongoing conversations keyed by session_id
        self._memory: Dict[str, Plan] = {}

    def _get_logger(self, session_id: str) -> SessionLogger:
        if session_id not in self._loggers:
            self._loggers[session_id] = SessionLogger(session_id)
        return self._loggers[session_id]

    def _merge_with_memory(self, session_id: str, incoming_plan: Plan) -> Plan:
        existing = self._memory.get(session_id)
        if not existing:
            return incoming_plan

        # If we have an existing intent awaiting clarification, prefer that intent
        intent: IntentName | None = existing.intent or incoming_plan.intent
        if not intent:
            return incoming_plan

        required = INTENT_TO_REQUIRED_SLOTS[intent]
        merged_slots: Dict[str, str | None] = {s: None for s in required}

        # Start with existing slots
        for k in required:
            if existing.slots.get(k):
                merged_slots[k] = existing.slots[k]

        # Overlay new detections
        for k in required:
            if incoming_plan.slots.get(k):
                merged_slots[k] = incoming_plan.slots[k]

        missing = [k for k in required if not merged_slots.get(k)]
        return Plan(intent=intent, slots=merged_slots, missing_slots=missing, rationale=incoming_plan.rationale)

    def _update_memory(self, session_id: str, plan: Plan) -> None:
        if plan.intent and plan.missing_slots:
            # Keep waiting state
            self._memory[session_id] = plan
        else:
            # Clear state when done
            if session_id in self._memory:
                del self._memory[session_id]

    def process(self, user_message: str, session_id: str | None = None) -> ChatResponse:
        sid = session_id or str(uuid.uuid4())
        logger = self._get_logger(sid)
        logger.user_message(user_message)

        planner = Planner(logger)
        reviewer = Reviewer(logger)
        executioner = Executioner(logger)
        responder = Responder(logger)

        incoming_plan: Plan = planner.run(user_message)
        # Merge with memory if we are mid-clarification
        plan: Plan = self._merge_with_memory(sid, incoming_plan)
        review = reviewer.run(plan)

        # If missing slots, ask for clarification in this turn and stop.
        if plan.intent and plan.missing_slots:
            assistant_msg = responder.run(plan, result=None)
            logger.assistant_message(assistant_msg.content)
            self._update_memory(sid, plan)
            return ChatResponse(
                session_id=sid,
                messages=[Message(role="user", content=user_message), assistant_msg],
                awaiting_user=True,
                missing_slots=plan.missing_slots,
                intent=plan.intent,
            )

        # Execute when plan is complete
        exec_result = executioner.run(plan)
        assistant_msg = responder.run(plan, exec_result)
        logger.assistant_message(assistant_msg.content)
        self._update_memory(sid, plan)

        return ChatResponse(
            session_id=sid,
            messages=[Message(role="user", content=user_message), assistant_msg],
            awaiting_user=False,
            missing_slots=[],
            intent=plan.intent,
        ) 