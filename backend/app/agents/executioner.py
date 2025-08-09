from __future__ import annotations

import random
import time
from typing import Any, Dict

from app.core.logger import SessionLogger
from app.core.types import ExecutionResult, IntentName, Plan


class Executioner:
    def __init__(self, logger: SessionLogger) -> None:
        self.logger = logger

    def run(self, plan: Plan) -> ExecutionResult:
        if plan.intent is None:
            result = ExecutionResult(success=False, error="No intent to execute", action_name=None, elapsed_ms=0)
            self.logger.step("executioner", {"plan": plan.model_dump()}, result.model_dump())
            return result

        start = time.perf_counter()
        action_name = plan.intent.value
        try:
            if plan.intent == IntentName.card_replace:
                ticket_id = f"CR-{random.randint(100000, 999999)}"
                data = {"ticket_id": ticket_id, **plan.slots}
                success = True

            elif plan.intent == IntentName.report_fraud:
                case_id = f"FR-{random.randint(100000, 999999)}"
                data = {"case_id": case_id, **plan.slots}
                success = True

            elif plan.intent == IntentName.open_account:
                application_id = f"OA-{random.randint(100000, 999999)}"
                data = {"application_id": application_id, **plan.slots}
                success = True

            elif plan.intent == IntentName.check_balance:
                balance = round(random.uniform(100.0, 5000.0), 2)
                data = {"balance": balance, **plan.slots}
                success = True

            elif plan.intent == IntentName.transfer_money:
                transfer_id = f"TX-{random.randint(100000, 999999)}"
                data = {"transfer_id": transfer_id, "status": "initiated", **plan.slots}
                success = True

            else:
                data = {}
                success = False
                error = "Unknown intent"

            elapsed_ms = int((time.perf_counter() - start) * 1000)
            result = ExecutionResult(
                success=success,
                data=data if success else {},
                error=None if success else error,
                action_name=action_name,
                elapsed_ms=elapsed_ms,
            )
        except Exception as ex:  # noqa: BLE001
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            result = ExecutionResult(
                success=False,
                data={},
                error=str(ex),
                action_name=action_name,
                elapsed_ms=elapsed_ms,
            )

        self.logger.step("executioner", {"plan": plan.model_dump()}, result.model_dump())
        return result 