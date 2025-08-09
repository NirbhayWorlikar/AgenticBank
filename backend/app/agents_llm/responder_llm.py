from __future__ import annotations

from app.llm.bedrock import call_llm_json, get_bedrock_client
from app.core.types import ExecutionResult


def summarize_result_llm(execution_result: ExecutionResult) -> str:
    llm = get_bedrock_client()
    prompt = f"""
You are a helpful, empathetic banking assistant. Summarize the following execution result for the user in a clear, friendly, and concise way. If there was an error, apologize and explain.
Execution Result: {execution_result.model_dump_json()}
Respond with a single user-facing message.
"""
    response = call_llm_json(prompt, llm)
    if isinstance(response, str):
        return response
    if isinstance(response, dict) and 'message' in response:
        return response['message']
    return "Thank you for using our banking assistant. If you need further help, please let us know!" 