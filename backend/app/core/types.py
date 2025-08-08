from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class IntentName(str, Enum):
    card_replace = "card_replace"
    report_fraud = "report_fraud"
    open_account = "open_account"
    check_balance = "check_balance"
    transfer_money = "transfer_money"


INTENT_TO_REQUIRED_SLOTS: Dict[IntentName, List[str]] = {
    IntentName.card_replace: ["card_type", "delivery_address", "reason"],
    IntentName.report_fraud: ["transaction_id", "fraud_type", "user_confirmation"],
    IntentName.open_account: ["account_type", "customer_name", "id_proof"],
    IntentName.check_balance: ["account_number", "auth_token"],
    IntentName.transfer_money: ["sender_account", "receiver_account", "amount"],
}


class Message(BaseModel):
    role: Literal[
        "user",
        "assistant",
        "planner",
        "reviewer",
        "executioner",
        "responder",
        "system",
    ] = "assistant"
    content: str


class Plan(BaseModel):
    intent: Optional[IntentName]
    slots: Dict[str, Optional[str]] = Field(default_factory=dict)
    missing_slots: List[str] = Field(default_factory=list)
    rationale: str = ""


class Review(BaseModel):
    approved: bool
    issues: List[str] = Field(default_factory=list)
    score: float = 0.0


class ExecutionResult(BaseModel):
    success: bool
    data: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None


class AgentStep(BaseModel):
    name: str
    input: Dict[str, Any] = Field(default_factory=dict)
    output: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    message: str
    metadata: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    session_id: str
    messages: List[Message]
    awaiting_user: bool = False
    missing_slots: List[str] = Field(default_factory=list)
    intent: Optional[IntentName] = None 