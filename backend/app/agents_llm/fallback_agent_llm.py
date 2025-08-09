from __future__ import annotations

from app.llm.bedrock import call_llm_json, get_bedrock_client


def fallback_response_llm(user_message: str, reason: str) -> str:
    llm = get_bedrock_client()
    prompt = f"""
You are a fallback banking assistant. The main workflow could not process the user's request due to: {reason}.
Generate a helpful, apologetic, and informative response to the user, suggesting next steps or alternative actions if possible.
User message: {user_message}
Respond with a single user-facing message.
"""
    response = call_llm_json(prompt, llm)
    if isinstance(response, str):
        return response
    if isinstance(response, dict) and 'message' in response:
        return response['message']
    return "Sorry, we couldn't process your request at this time. Please try again later or contact support." 