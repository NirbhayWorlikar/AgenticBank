## AgenticBank PoC

An agentic banking assistant demonstrating an end-to-end flow for common retail banking intents with a multi-agent architecture and a simple React UI.

- Planner → Reviewer → Executioner → Responder pipeline
- Session-wise JSONL logging for traceability
- Clarification loop with kind and empathetic prompts
- Rule-based NLU for PoC (AWS Bedrock wiring planned next)

---

### Architecture
- **Planner**: Detects intent and extracts slots from user input (rule-based NLU for PoC).
- **Reviewer**: Scores plan for completeness and basic safety per PoC; approves even if slots are missing (to trigger clarification).
- **Executioner**: Simulates actions for the intent and returns mock results (no real banking APIs).
- **Responder**: Produces empathetic, user-friendly replies. When slots are missing, asks clarifying questions.
- **Pipeline**: Orchestrates all agents and maintains simple session memory to merge slot values across turns.

### Supported Intents and Required Slots
- **card_replace**: `card_type`, `delivery_address`, `reason`
- **report_fraud**: `transaction_id`, `fraud_type`, `user_confirmation`
- **open_account**: `account_type`, `customer_name`, `id_proof`
- **check_balance**: `account_number`, `auth_token`
- **transfer_money**: `sender_account`, `receiver_account`, `amount`

### Tech Stack
- **Backend**: FastAPI, Pydantic, Uvicorn
- **Agents**: Python classes (Planner, Reviewer, Executioner, Responder) with a simple pipeline
- **LLM**: Rule-based NLU for PoC (Bedrock + LangGraph-AWS planned)
- **Frontend**: React + Vite (TypeScript)
- **Logging**: Session-wise JSONL files

### Repo Structure
```
AgenticBank/
  ├─ backend/
  │  ├─ app/
  │  │  ├─ agents/
  │  │  │  ├─ planner.py
  │  │  │  ├─ reviewer.py
  │  │  │  ├─ executioner.py
  │  │  │  └─ responder.py
  │  │  ├─ core/
  │  │  │  ├─ types.py
  │  │  │  ├─ logger.py
  │  │  │  ├─ nlu.py
  │  │  │  └─ pipeline.py
  │  │  └─ main.py
  │  ├─ requirements.txt
  │  └─ sample_queries.py
  └─ frontend/
     ├─ package.json
     ├─ tsconfig.json
     ├─ vite.config.ts
     ├─ index.html
     └─ src/
        ├─ main.tsx
        ├─ App.tsx
        └─ styles.css
```

---

## Backend

### Setup
```bash
python3 -m venv AgenticBank/.venv
source AgenticBank/.venv/bin/activate
pip install -r AgenticBank/backend/requirements.txt
```

### Run
```bash
uvicorn app.main:app \
  --app-dir AgenticBank/backend \
  --host 0.0.0.0 --port 8000 --reload
```

### Healthcheck
```bash
curl -s http://127.0.0.1:8000/health
```

### Chat API
- URL: `POST /chat`
- Request body:
```json
{
  "session_id": "optional-string",
  "message": "user text"
}
```
- Response body (example):
```json
{
  "session_id": "uuid",
  "messages": [
    { "role": "user", "content": "..." },
    { "role": "assistant", "content": "..." }
  ],
  "awaiting_user": true,
  "missing_slots": ["card_type", "reason"],
  "intent": "card_replace"
}
```
- Notes:
  - When required slots are missing, `awaiting_user` is true and the assistant asks an empathetic clarifying question.
  - Session memory merges newly provided slot values across subsequent user messages.

### Sample cURL
```bash
# Card replacement in one turn
curl -s -X POST http://127.0.0.1:8000/chat \
  -H 'Content-Type: application/json' \
  -d '{"message":"I lost my credit card, my address is 123 Main St, please replace it"}' | jq .

# Two-turn clarification example
sid=$(curl -s -X POST http://127.0.0.1:8000/chat -H 'Content-Type: application/json' \
  -d '{"message":"Please replace my card"}' | jq -r .session_id)

curl -s -X POST http://127.0.0.1:8000/chat -H 'Content-Type: application/json' \
  -d '{"message":"credit, ship to 456 Oak Ave, it\'s lost", "session_id":"'"$sid"'"}' | jq .
```

### Sample Python script
```bash
source AgenticBank/.venv/bin/activate
python AgenticBank/backend/sample_queries.py
```

### Logging
- Location: `AgenticBank/logs/session_<SESSION_ID>.jsonl`
- Format: line-delimited JSON with fields: `ts`, `session_id`, `event`, `payload`
- Events: `user_message`, `assistant_message`, `agent_step` (planner/reviewer/executioner/responder), `info`

---

## Frontend

### Setup
```bash
cd AgenticBank/frontend
npm install
```

### Run
```bash
npm run dev
```
- Open the printed URL (typically `http://localhost:5173`).
- Backend URL defaults to `http://127.0.0.1:8000`. To override, create `AgenticBank/frontend/.env`:
```
VITE_API_URL=http://127.0.0.1:8000
```

### UI behavior
- Messages appear in a chat layout; Enter key sends.
- Session ID is persisted in `localStorage` to continue multi-turn clarifications.
- Assistant uses an empathetic tone tailored to the detected intent when asking for missing slots.

---

## Safety and Constraints
- Reviewer performs basic plan completeness and PoC safety checks as outlined in the IDEA doc.
- No real banking APIs; all execution is simulated with mock IDs and values.
- English-only; latency may be observable depending on environment.

---

## Future Work
- Replace rule-based NLU with **AWS Bedrock** (Claude Sonnet v3.5) via **LangGraph-AWS** for Planner/Reviewer/Responder.
- Expand safety and compliance policies; add more granular checks.
- Richer analytics in logs (step IDs, durations, token counts when LLM is wired).
- Optional vector store for semantic memory (not needed for PoC).
- Add unit tests and e2e tests for intents and clarification flows.

---

## Sample Intents to Try
- "I lost my credit card, my address is 123 Main St, please replace it"
- "Report fraud on transaction ID TX-12345"
- "Open a savings account, my name is Jane Doe"
- "Check balance for account number 123456 with token ABCD"
- "Transfer 250 from 111111 to 222222" 