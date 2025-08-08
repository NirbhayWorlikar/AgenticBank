## AgenticBank PoC

An agentic banking assistant demonstrating an end-to-end flow for common retail banking intents with a multi-agent architecture and a simple React UI.

- Planner → Reviewer → Executioner → Reviewer → Responder pipeline
- Session-wise JSONL logging for traceability
- Clarification loop with kind and empathetic prompts
- Rule-based NLU for PoC with optional AWS Bedrock LLM wiring via langchain-aws

---

### Architecture
- Planner (rule-based or LLM)
- Reviewer (rule-based or LLM), reviewing both plan and execution
- Executioner (mock actions only)
- Responder (empathetic language)
- Pipeline managing session state: idle → awaiting_clarification → executing → completed → idle

### Supported Intents and Required Slots
- card_replace: card_type, delivery_address, reason
- report_fraud: transaction_id, fraud_type, user_confirmation
- open_account: account_type, customer_name, id_proof
- check_balance: account_number, auth_token
- transfer_money: sender_account, receiver_account, amount

### Tech Stack
- Backend: FastAPI, Pydantic, Uvicorn
- Agents: Python classes; optional AWS Bedrock LLM agents via langchain-aws
- Orchestration: Simple pipeline (LangGraph sample included for future migration)
- Frontend: React + Vite (TypeScript)
- Logging: Session-wise JSONL files

### Repo Structure
```
AgenticBank/
  ├─ backend/
  │  ├─ app/
  │  │  ├─ agents/ (rule-based)
  │  │  ├─ agents_llm/ (AWS Bedrock via langchain-aws)
  │  │  ├─ core/ (types, logger, nlu, pipeline)
  │  │  ├─ graph/ (LangGraph example)
  │  │  └─ main.py
  │  ├─ requirements.txt
  │  ├─ sample_queries.py
  │  └─ tests/ (pytest)
  └─ frontend/ (Vite React UI)
```

---

## Backend

### Setup
```
python3 -m venv AgenticBank/.venv
source AgenticBank/.venv/bin/activate
pip install -r AgenticBank/backend/requirements.txt
```

### Run
```
uvicorn app.main:app \
  --app-dir AgenticBank/backend \
  --host 0.0.0.0 --port 8000 --reload
```

### Healthcheck
```
curl -s http://127.0.0.1:8000/health
```

### Chat API
- POST /chat
- Request: { "session_id": "optional", "message": "text" }
- Response: { session_id, messages, awaiting_user, missing_slots, intent, state }

### Empathetic Clarification
- If required slots are missing, the responder prompts with kind, intent-specific wording.
- Session memory merges new slot values across turns.

### Logging
- Location: `AgenticBank/backend/logs/session_<SESSION_ID>.jsonl`
- Events: user_message, assistant_message, agent_step, state_transition, info

---

## AWS Bedrock + LLM Wiring (Optional)
- Requires AWS credentials configured (env or IAM role)
- Environment flags:
```
export USE_LLM=true
export AWS_REGION=us-east-1
export BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20240620-v1:0
# Optional: BEDROCK_TEMPERATURE (default 0.2), BEDROCK_MAX_TOKENS (default 1024)
```
- LLM planner: `app/agents_llm/planner_llm.py` (extracts intent/slots as JSON)
- LLM reviewer: `app/agents_llm/reviewer_llm.py` (reviews plan and execution)
- Pipeline will switch automatically when `USE_LLM=true`.

Note: Network access to Bedrock must be available from your environment.

---

## Frontend

### Setup
```
cd AgenticBank/frontend
npm install
```

### Run
```
npm run dev
```
- Open the printed URL (typically http://localhost:5173)
- Backend URL defaults to http://127.0.0.1:8000. To override, create `.env`:
```
VITE_API_URL=http://127.0.0.1:8000
```

---

## Tests

### Run tests
```
cd AgenticBank/backend
PYTHONPATH=. pytest -q
```
- 8 tests cover: NLU, pipeline flows, and API endpoint

---

## Sample Usage
- "I lost my credit card, my address is 123 Main St, please replace it"
- "Please replace my card" → assistant asks for card_type/reason/address
- "transfer 250 from 111111 to 222222"

---

## Future Work
- Migrate orchestration onto LangGraph nodes fully
- Expand safety/compliance checks in reviewer
- Add more intents/slots and richer UI interactions 

---

## Prerequisites
- Python 3.9+
- Node.js 18+ (20/22 recommended)
- AWS credentials configured (only if `USE_LLM=true`)

Environment variables (optional):
- `USE_LLM` (true/false): switch to AWS Bedrock LLM agents
- `AWS_REGION` (e.g., `us-east-1`)
- `BEDROCK_MODEL_ID` (e.g., `anthropic.claude-3-5-sonnet-20240620-v1:0`)
- `BEDROCK_TEMPERATURE` (default 0.2)
- `BEDROCK_MAX_TOKENS` (default 1024)

---

## API Schemas

ChatRequest
```
{
  "session_id": "optional-string",
  "message": "user text",
  "metadata": { "optional": "object" }
}
```

ChatResponse
```
{
  "session_id": "uuid",
  "messages": [ { "role": "user|assistant", "content": "..." } ],
  "awaiting_user": true|false,
  "missing_slots": ["card_type", "reason"],
  "intent": "card_replace|report_fraud|open_account|check_balance|transfer_money|null",
  "state": "idle|awaiting_clarification|executing|completed"
}
```

---

## Session Behavior and Memory
- State machine: idle → awaiting_clarification → executing → completed → idle
- Clarification loop: If required slots are missing, the system asks empathetic follow-up questions
- Slot-only replies: When awaiting clarification, if the user sends only slot values (e.g., "credit", "ship to 123 Main St"), the system extracts slots using the previous intent and merges them into the active plan
- Commands:
  - Cancel/reset: "cancel", "stop", "never mind", "reset", "start over"
  - New request: "new request", "new intent", or "different request"

Reviewer calls per turn:
- After Planner: plan review (completeness/safety) determines whether to clarify or proceed
- After Executioner: execution review validates result (e.g., transfer_id/balance present)

---

## Sample cURL
Single turn
```
curl -s -X POST http://127.0.0.1:8000/chat \
  -H 'Content-Type: application/json' \
  -d '{"message":"I lost my credit card, my address is 123 Main St, please replace it"}' | jq .
```

Multi-turn (clarification)
```
# Turn 1 – missing slots → system asks follow-up
sid=$(curl -s -X POST http://127.0.0.1:8000/chat -H 'Content-Type: application/json' \
  -d '{"message":"Please replace my card"}' | jq -r .session_id)

# Turn 2 – slot-only reply; system merges slots from previous intent
curl -s -X POST http://127.0.0.1:8000/chat -H 'Content-Type: application/json' \
  -d '{"message":"credit, ship to 456 Oak Ave, it\'s lost", "session_id":"'"$sid"'"}' | jq .
```

---

## Troubleshooting
- Port already in use (8000):
  - `lsof -i :8000 -sTCP:LISTEN | awk 'NR>1{print $2}' | xargs -r kill -9`
- Frontend Vite fails with missing `@vitejs/plugin-react`:
  - Ensure you are in `AgenticBank/frontend`
  - `rm -rf node_modules package-lock.json && npm install`
  - `npm ls @vitejs/plugin-react` should list the plugin
  - Node must be 18+
- Tests cannot import `app`:
  - Run with `PYTHONPATH=.` from `AgenticBank/backend` (e.g., `PYTHONPATH=. pytest -q`)
- Bedrock access:
  - Ensure AWS credentials and region are set; verify `BEDROCK_MODEL_ID`

--- 