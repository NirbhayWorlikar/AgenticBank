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

        empathetic_templates = {
            IntentName.card_replace: (
                "I'm sorry to hear about your card. I'll help you get a replacement right away. "
                f"To proceed, could you please share: {readable}?"
            ),
            IntentName.report_fraud: (
                "That sounds stressful, and your security matters. I'll help you report this. "
                f"Please provide: {readable}."
            ),
            IntentName.open_account: (
                "Happy to help you open an account. We'll make this quick. "
                f"To get started, please share: {readable}."
            ),
            IntentName.check_balance: (
                "I can help you check your balance. "
                f"Please provide: {readable}."
            ),
            IntentName.transfer_money: (
                "I can help with your transfer. "
                f"Please provide: {readable}."
            ),
        }

        base = empathetic_templates.get(intent)
        if not base:
            base = (
                f"I can help with {human_intent}. To proceed, please provide: {readable}."
            )
        return base + " Thank you!"

    def _final_response(self, plan: Plan, result: ExecutionResult) -> str:
        if not result.success:
            return f"I couldn't complete the request: {result.error}"

        if plan.intent == IntentName.card_replace:
            return (
                "Your card replacement request is submitted. "
                f"Ticket {result.data.get('ticket_id')} — {plan.slots.get('card_type')} card will be sent to "
                f"{plan.slots.get('delivery_address')}."
            )
        if plan.intent == IntentName.report_fraud:
            return (
                "Thanks. We've opened a fraud investigation. "
                f"Case {result.data.get('case_id')} — we'll update you within 2 business days."
            )
        if plan.intent == IntentName.open_account:
            return (
                "Your account application is created. "
                f"Application {result.data.get('application_id')} for a {plan.slots.get('account_type')} account."
            )
        if plan.intent == IntentName.check_balance:
            return f"Your account balance is ${result.data.get('balance')}"
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