from __future__ import annotations

import os
from typing import List

import orjson
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse

from app.core.pipeline import AgentPipeline
from app.core.types import ChatRequest, ChatResponse


def _orjson_dumps(v, *, default):
    return orjson.dumps(v, default=default).decode()


app = FastAPI(title="AgenticBank API", default_response_class=ORJSONResponse)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

pipeline = AgentPipeline()


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    return pipeline.process(req.message, session_id=req.session_id)


# Local dev convenience: uvicorn entry point
if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True) 