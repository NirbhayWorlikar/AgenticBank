from __future__ import annotations

from app.llm.bedrock import call_llm_json, get_bedrock_client
from app.core.types import ExecutionResult


def summarize_result_llm(execution_result: ExecutionResult) -> str:
    llm = get_bedrock_client()
    prompt = f"""
You are a banking assistant. Be empathetic and concise.
Summarize the execution result for the user in 1–2 short sentences. Avoid extra detail, no code, no JSON, no system messages.
If there was an error, apologize briefly and explain in one sentence.
Execution Result: {execution_result.model_dump_json()}
Respond ONLY with the final user-facing message.
"""
    response = call_llm_json(prompt, llm)
    if isinstance(response, str):
        return response.strip()
    if isinstance(response, dict) and 'message' in response:
        return str(response['message']).strip()
    return "Thanks for your patience — your request is complete. If you need anything else, I’m here to help." 