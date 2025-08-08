from __future__ import annotations

from typing import Any, Dict

from langgraph.graph import END, START, StateGraph

# Placeholder: We keep our existing pipeline orchestrator. This graph demonstrates
# how to wire nodes; later we can fully migrate nodes to use the LLM agents.


def build_dummy_graph() -> StateGraph:
    g = StateGraph(dict)

    def planner_node(state: Dict[str, Any]) -> Dict[str, Any]:
        # Pass-through for now
        return state

    def reviewer_node(state: Dict[str, Any]) -> Dict[str, Any]:
        return state

    def executioner_node(state: Dict[str, Any]) -> Dict[str, Any]:
        return state

    def responder_node(state: Dict[str, Any]) -> Dict[str, Any]:
        return state

    g.add_node("planner", planner_node)
    g.add_node("reviewer", reviewer_node)
    g.add_node("executioner", executioner_node)
    g.add_node("responder", responder_node)

    g.add_edge(START, "planner")
    g.add_edge("planner", "reviewer")
    g.add_edge("reviewer", "executioner")
    g.add_edge("executioner", "responder")
    g.add_edge("responder", END)
    return g 