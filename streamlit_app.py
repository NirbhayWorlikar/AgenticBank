from __future__ import annotations

import glob
import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import streamlit as st


def get_logs_dir() -> str:
    # Allow override via env; default to backend/logs relative to this file
    env_dir = os.getenv("LOGS_DIR")
    if env_dir:
        return env_dir
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(here, "backend", "logs")


def list_session_files(logs_dir: str) -> List[str]:
    pattern = os.path.join(logs_dir, "session_*.jsonl")
    files = glob.glob(pattern)
    files.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    return files


def read_jsonl(path: str) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except Exception:
                    # Skip malformed lines
                    continue
    except FileNotFoundError:
        return []
    return records


def format_ts(ts: Optional[str]) -> str:
    if not ts:
        return ""
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return ts


def event_palette(event: str) -> str:
    return {
        "user_message": "#1f6feb",
        "assistant_message": "#3fb950",
        "agent_step": "#9e6ffe",
        "state_transition": "#ffa657",
        "chat_response": "#d29922",
        "info": "#8b949e",
    }.get(event, "#8b949e")


def render_event(rec: Dict[str, Any]) -> None:
    ts = rec.get("ts")
    ev = rec.get("event")
    payload = rec.get("payload", {})
    color = event_palette(ev)

    with st.container():
        st.markdown(f"<div style='color:{color};font-weight:600'>{ev}</div>", unsafe_allow_html=True)
        if ts:
            st.caption(format_ts(ts))

        if ev == "user_message":
            st.markdown(f"User: {payload.get('message','')}")
        elif ev == "assistant_message":
            st.markdown(f"Assistant: {payload.get('message','')}")
        elif ev == "agent_step":
            name = payload.get("name", "agent")
            with st.expander(f"Agent step: {name}"):
                st.write("Input:")
                st.json(payload.get("input", {}), expanded=False)
                st.write("Output:")
                st.json(payload.get("output", {}), expanded=False)
        elif ev == "state_transition":
            st.markdown(f"State: {payload.get('from')} → {payload.get('to')}")
        elif ev == "chat_response":
            with st.expander("ChatResponse"):
                st.json(payload, expanded=False)
        else:
            st.json(payload, expanded=False)


def main() -> None:
    st.set_page_config(page_title="AgenticBank Logs", layout="wide")
    st.title("AgenticBank – Session Logs")

    logs_dir = get_logs_dir()
    st.sidebar.header("Controls")
    st.sidebar.write(f"Logs dir: {logs_dir}")

    # Auto-refresh toggle
    auto = st.sidebar.checkbox("Auto-refresh", value=True)
    interval_s = st.sidebar.slider("Refresh interval (sec)", min_value=1, max_value=10, value=3)
    if auto:
        st.experimental_set_query_params(_=datetime.utcnow().timestamp())
        st.experimental_rerun  # no-op placeholder for type checkers
        try:
            # st_autorefresh is available on recent Streamlit versions
            from streamlit_autorefresh import st_autorefresh  # type: ignore

            st_autorefresh(interval=interval_s * 1000, key="auto")
        except Exception:
            # Fallback: a light timer using empty write (no strict guarantee)
            pass

    files = list_session_files(logs_dir)
    if not files:
        st.info("No session logs found yet. Start chatting with the backend to generate logs.")
        return

    # Choose session (default: latest)
    file_labels = [os.path.basename(p) for p in files]
    default_idx = 0
    choice = st.sidebar.selectbox("Session", options=list(range(len(files))), format_func=lambda i: file_labels[i], index=default_idx)
    path = files[choice]

    # Filters
    st.sidebar.subheader("Event filters")
    show_user = st.sidebar.checkbox("user_message", value=True)
    show_assistant = st.sidebar.checkbox("assistant_message", value=True)
    show_agent = st.sidebar.checkbox("agent_step", value=True)
    show_state = st.sidebar.checkbox("state_transition", value=True)
    show_resp = st.sidebar.checkbox("chat_response", value=False)
    show_info = st.sidebar.checkbox("info", value=False)
    filters = {
        "user_message": show_user,
        "assistant_message": show_assistant,
        "agent_step": show_agent,
        "state_transition": show_state,
        "chat_response": show_resp,
        "info": show_info,
    }

    st.subheader(os.path.basename(path))
    try:
        mtime = os.path.getmtime(path)
        st.caption(f"Updated: {datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')}")
    except Exception:
        pass

    records = read_jsonl(path)
    if not records:
        st.warning("Log file is empty.")
        return

    # Render events respecting filters
    for rec in records:
        ev = rec.get("event")
        if ev not in filters or not filters[ev]:
            continue
        render_event(rec)
        st.divider()

    # Raw download
    with open(path, "rb") as f:
        st.download_button("Download log file", data=f, file_name=os.path.basename(path), mime="text/plain")


if __name__ == "__main__":
    main()


