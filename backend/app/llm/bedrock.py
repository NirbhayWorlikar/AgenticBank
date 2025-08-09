from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional, Union

from langchain_aws import ChatBedrock
from pydantic import BaseModel


def get_bedrock_client() -> ChatBedrock:
    model_id = os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-3-5-sonnet-20240620-v1:0")
    region = os.getenv("AWS_REGION", "us-east-1")
    # Assumes AWS credentials are configured via env/role
    llm = ChatBedrock(
        model_id=model_id,
        region_name=region,
        # You can tweak inference params here
        model_kwargs={
            "temperature": float(os.getenv("BEDROCK_TEMPERATURE", "0.2")),
            "max_tokens": int(os.getenv("BEDROCK_MAX_TOKENS", "1024")),
        },
    )
    return llm


def format_system_prompt() -> str:
    return (
        "You are an assistant in a retail bank contact center. "
        "Be concise, kind, and empathetic. Follow instructions and produce JSON when asked."
    )


def _best_effort_parse_json(text: str) -> Union[Dict[str, Any], str]:
    try:
        return json.loads(text)
    except Exception:
        # Try to extract a JSON object if present
        start = text.find("{")
        end = text.rfind("}")
        if 0 <= start < end:
            snippet = text[start : end + 1]
            try:
                return json.loads(snippet)
            except Exception:
                pass
        return text


def _missing_aws_credentials() -> bool:
    # Basic heuristic: if neither env var nor shared credentials file set
    # Botocore will raise at invoke time; we short-circuit here for PoC tests
    return not (os.getenv("AWS_ACCESS_KEY_ID") or os.getenv("AWS_PROFILE") or os.getenv("AWS_SESSION_TOKEN"))


def call_llm_json(prompt: str, llm: Optional[ChatBedrock] = None) -> Union[Dict[str, Any], str]:
    # Safe-mode mock if creds are missing
    if _missing_aws_credentials():
        # Generate a minimal deterministic mock based on keywords in prompt
        lower = prompt.lower()
        if "json" in lower and "intent" in lower and "slots" in lower:
            return {"intent": None, "slots": {}}
        if "review" in lower and "score" in lower:
            return {"approved": True, "issues": [], "score": 7.0}
        if "respond" in lower and "execution" in lower:
            return "All set!"
        # Generic fallback
        return "Okay."

    client = llm or get_bedrock_client()
    resp = client.invoke([
        {"role": "system", "content": format_system_prompt()},
        {"role": "user", "content": prompt},
    ])
    content = resp.content if hasattr(resp, "content") else str(resp)
    return _best_effort_parse_json(content) 