from __future__ import annotations

from typing import List

from app.core.logger import SessionLogger
from app.core.types import ExecutionResult, IntentName, Message, Plan


class Responder:
    def __init__(self, logger: SessionLogger) -> None:
        self.logger = logger

    def _clarify_prompt(self, intent: IntentName, missing_slots: List[str]) -> str:
        readable = ", ".join(missing_slots)
        human_intent = intent.value.replace("_", " ")

        templates = {
            IntentName.card_replace: f"I’m sorry about your card. To proceed, please share: {readable}.",
            IntentName.report_fraud: f"I understand your concern. To report this, please provide: {readable}.",
            IntentName.open_account: f"Happy to help you open an account. Please share: {readable}.",
            IntentName.check_balance: f"I can help check your balance. Please provide: {readable}.",
            IntentName.transfer_money: f"I can help with the transfer. Please provide: {readable}.",
        }

        return templates.get(intent, f"To help with {human_intent}, please provide: {readable}.")

    def _final_response(self, plan: Plan, result: ExecutionResult) -> str:
        if not result.success:
            return f"Sorry, I couldn’t complete that: {result.error}"

        if plan.intent == IntentName.card_replace:
            return (
                "Your card replacement is submitted. "
                f"Ticket {result.data.get('ticket_id')} — {plan.slots.get('card_type')} card will be sent to "
                f"{plan.slots.get('delivery_address')}."
            )
        if plan.intent == IntentName.report_fraud:
            return (
                "We’ve opened a fraud case. "
                f"Case {result.data.get('case_id')} — we’ll update you soon."
            )
        if plan.intent == IntentName.open_account:
            return (
                "Your application is created. "
                f"ID {result.data.get('application_id')} for a {plan.slots.get('account_type')} account."
            )
        if plan.intent == IntentName.check_balance:
            return f"Your balance is ${result.data.get('balance')}"
        if plan.intent == IntentName.transfer_money:
            return (
                f"Transfer initiated (ID {result.data.get('transfer_id')}). "
                f"Amount {plan.slots.get('amount')} to {plan.slots.get('receiver_account')}."
            )
        return "Done."

    def run(self, plan: Plan, result: ExecutionResult | None) -> Message:
        if plan.intent and plan.missing_slots:
            content = self._clarify_prompt(plan.intent, plan.missing_slots)
        else:
            assert result is not None, "Execution result required when no missing slots"
            content = self._final_response(plan, result)

        message = Message(role="assistant", content=content)
        self.logger.step("responder", {"plan": plan.model_dump(), "result": (result.model_dump() if result else None)}, message.model_dump())
        return message 