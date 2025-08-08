from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict


class SessionLogger:
    def __init__(self, session_id: str, base_dir: str | None = None) -> None:
        self.session_id = session_id
        logs_dir = base_dir or os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "..", "logs"
        )
        self.logs_dir = os.path.abspath(logs_dir)
        Path(self.logs_dir).mkdir(parents=True, exist_ok=True)
        self.file_path = os.path.join(self.logs_dir, f"session_{self.session_id}.jsonl")

    def write(self, event_type: str, payload: Dict[str, Any]) -> None:
        record = {
            "ts": datetime.utcnow().isoformat(timespec="seconds") + "Z",
            "session_id": self.session_id,
            "event": event_type,
            "payload": payload,
        }
        with open(self.file_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def step(self, name: str, input_data: Dict[str, Any], output_data: Dict[str, Any]) -> None:
        self.write(
            "agent_step",
            {"name": name, "input": input_data, "output": output_data},
        )

    def user_message(self, message: str) -> None:
        self.write("user_message", {"message": message})

    def assistant_message(self, message: str) -> None:
        self.write("assistant_message", {"message": message})

    def info(self, message: str, **kwargs: Any) -> None:
        payload = {"message": message, **kwargs}
        self.write("info", payload) 