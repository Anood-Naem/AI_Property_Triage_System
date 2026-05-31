"""LangGraph agent: planner -> tools -> synthesiser."""

import logging
import sys
from pathlib import Path
from typing import Any, TypedDict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langgraph.graph import END, StateGraph

from common.schemas import route_listing_team
from common.image_sources import ImageSource
from tools import analyse_all_images, call_rag

logger = logging.getLogger(__name__)


class AgentState(TypedDict, total=False):
    query: str
    description: str
    image_urls: list[str]
    images: list[dict[str, Any]]
    plan: str
    tools_to_run: list[str]
    rag_result: dict[str, Any]
    image_results: list[dict[str, Any]]
    tools_used: list[str]
    reasoning_steps: list[str]
    answer: str
    recommended_team: str


def planner_node(state: AgentState) -> AgentState:
    query = state.get("query", "")
    urls = state.get("image_urls", [])
    uploads = state.get("images", [])
    n_images = len(urls) + len(uploads)
    steps = ["Planner: run RAG for similar-listing comparison."]
    tools = ["rag_tool"]
    if n_images:
        tools.append("image_analyser_tool")
        steps.append(f"Planner: analyse {n_images} image(s) (URL and/or upload) for room condition.")
    return {
        **state,
        "plan": f"Execute tools {tools} for query: {query[:180]}",
        "tools_to_run": tools,
        "reasoning_steps": list(state.get("reasoning_steps", [])) + steps,
    }


def tool_execution_node(state: AgentState) -> AgentState:
    description = (state.get("description") or state.get("query") or "").strip()
    image_urls = state.get("image_urls", [])
    upload_models = [ImageSource.model_validate(item) for item in state.get("images", [])]
    tools_used: list[str] = []
    reasoning = list(state.get("reasoning_steps", []))

    rag_result: dict[str, Any] = {}
    if "rag_tool" in state.get("tools_to_run", []):
        rag_result = call_rag(description)
        tools_used.append("rag_tool")
        n = len(rag_result.get("similar_listings", []))
        reasoning.append(f"Tool rag_tool: retrieved {n} similar listing(s).")

    image_results: list[dict[str, Any]] = []
    if "image_analyser_tool" in state.get("tools_to_run", []) and (
        image_urls or upload_models
    ):
        image_results = analyse_all_images(image_urls, upload_models)
        tools_used.append("image_analyser_tool")
        reasoning.append(
            f"Tool image_analyser_tool: scored {len(image_results)} image(s)."
        )

    return {
        **state,
        "rag_result": rag_result,
        "image_results": image_results,
        "tools_used": tools_used,
        "reasoning_steps": reasoning,
    }


def synthesiser_node(state: AgentState) -> AgentState:
    query = state.get("query", "")
    rag = state.get("rag_result", {})
    images = state.get("image_results", [])
    reasoning = list(state.get("reasoning_steps", []))

    rag_summary = rag.get("insight", "No RAG insight available.")
    similar = rag.get("similar_listings", [])
    if similar:
        cited = ", ".join(item.get("id", "?") for item in similar[:3])
        rag_summary += f" Cited listing IDs: {cited}."

    image_lines: list[str] = []
    low_rooms: list[str] = []
    for img in images:
        room = img.get("room_type", "unknown")
        score = img.get("condition_score")
        url = img.get("image_url", "image")
        image_lines.append(f"- {url}: {room}, condition={score}, status={img.get('status')}")
        if score is not None and score < 4:
            low_rooms.append(room)

    parts = [
        f"**Query:** {query}",
        "",
        "**Market comparison (RAG):**",
        rag_summary,
        "",
        "**Image condition:**",
        "\n".join(image_lines) if image_lines else "No images analysed.",
    ]

    if low_rooms:
        unique = sorted(set(low_rooms))
        parts.extend(
            [
                "",
                "**Rooms needing attention:** " + ", ".join(unique),
                "To reach condition score 5, prioritize renovation in these areas "
                "based on image scores (facts from analysis only).",
            ]
        )
    else:
        parts.append(
            "\n**Renovation:** No critical low-score rooms detected; minor refreshes may suffice."
        )

    if similar:
        parts.append(
            f"\n**Comparable inventory:** {len(similar)} similar past listing(s) retrieved — "
            "confirm pricing with current market before publishing."
        )

    answer = "\n".join(parts)
    reasoning.append("Synthesiser: combined RAG and image evidence into final answer.")

    return {
        **state,
        "answer": answer,
        "reasoning_steps": reasoning,
        "recommended_team": route_listing_team(
            _infer_property_type(state, similar)
        ),
    }


def _infer_property_type(state: AgentState, similar: list[dict[str, Any]]) -> str | None:
    if similar:
        return similar[0].get("property_type")
    desc = (state.get("description") or "").lower()
    for token in ("apartment", "villa", "house", "office", "retail", "industrial"):
        if token in desc:
            return token
    return None


def build_graph():
    workflow = StateGraph(AgentState)
    workflow.add_node("planner", planner_node)
    workflow.add_node("tools", tool_execution_node)
    workflow.add_node("synthesiser", synthesiser_node)
    workflow.set_entry_point("planner")
    workflow.add_edge("planner", "tools")
    workflow.add_edge("tools", "synthesiser")
    workflow.add_edge("synthesiser", END)
    return workflow.compile()


_agent_graph = None


def get_graph():
    global _agent_graph
    if _agent_graph is None:
        _agent_graph = build_graph()
    return _agent_graph


def run_agent(
    query: str,
    description: str = "",
    image_urls: list[str] | None = None,
    images: list[ImageSource] | None = None,
) -> dict[str, Any]:
    graph = get_graph()
    initial: AgentState = {
        "query": query,
        "description": description or query,
        "image_urls": image_urls or [],
        "images": [img.model_dump() for img in (images or [])],
        "reasoning_steps": [],
        "tools_used": [],
    }
    result = graph.invoke(initial)
    return {
        "answer": result.get("answer", ""),
        "tools_used": result.get("tools_used", []),
        "reasoning_steps": result.get("reasoning_steps", []),
        "rag_result": result.get("rag_result", {}),
        "image_results": result.get("image_results", []),
        "recommended_team": result.get("recommended_team", "manual_review"),
    }
