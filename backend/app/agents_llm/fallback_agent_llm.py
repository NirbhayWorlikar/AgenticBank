from __future__ import annotations

from app.llm.bedrock import call_llm_json, get_bedrock_client


def fallback_response_llm(user_message: str, reason: str) -> str:
    llm = get_bedrock_client()
    prompt = f"""
You are a banking assistant. Be empathetic and concise.
Write a single short sentence to help the user proceed after this issue: {reason}.
Avoid code/JSON; ask for specific next steps or information if applicable.
User message: {user_message}
Respond ONLY with the final user-facing sentence.
"""
    response = call_llm_json(prompt, llm)
    if isinstance(response, str):
        return response.strip()
    if isinstance(response, dict) and 'message' in response:
        return str(response['message']).strip()
    return "Sorry, I couldn’t process that—please share the requested details and I’ll help right away." 