from __future__ import annotations

import os
from typing import Any, Dict, Optional

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


def call_llm_json(llm: ChatBedrock, prompt: str) -> str:
    # Simple wrapper; downstream parsers will handle JSON
    resp = llm.invoke([{"role": "system", "content": format_system_prompt()}, {"role": "user", "content": prompt}])
    return resp.content if hasattr(resp, "content") else str(resp) 