"""LangChain create_agent runner for NL → Kuzu tools → answer + graph."""

from __future__ import annotations

from typing import Any

import kuzu

from app.agent_tools import GraphCollector, build_kuzu_tools
from app.config import google_api_key, langchain_model
from app.models import AgentAskResponse, GraphPayload

SYSTEM_PROMPT = """You are a police-case graph investigation assistant.
The graph has Person, Phone, Account nodes and OwnsPhone, OwnsAccount, Called, Transferred edges.

Workflow:
1. Use search_persons_tool to resolve names to person_id.
2. Use seed_person_tool(person_id) to load the person and owned phones/accounts.
3. Use expand_node_tool on Phone nodes to see Called edges, or Account for Transferred.
   Those edges are one per direction (source→target): calls have count and duration_sec; transfers have count and amount.
4. Answer in Korean based only on tool results. Be concise.
Do not invent ids. Prefer expanding at most a few key phones/accounts.
"""


class AgentUnavailableError(RuntimeError):
    """Raised when LLM credentials/model are not configured."""


def _extract_answer(result: dict[str, Any]) -> str:
    messages = result.get("messages") or []
    for msg in reversed(messages):
        content = getattr(msg, "content", None)
        if content is None and isinstance(msg, dict):
            content = msg.get("content")
        if isinstance(content, str) and content.strip():
            # skip pure tool-call placeholders
            if getattr(msg, "type", None) == "tool":
                continue
            msg_type = getattr(msg, "type", None) or (
                msg.get("type") if isinstance(msg, dict) else None
            )
            if msg_type in {"ai", "assistant", None} or msg.__class__.__name__ in {
                "AIMessage",
                "AIMessageChunk",
            }:
                # Prefer final AI text without tool_calls pending
                tool_calls = getattr(msg, "tool_calls", None)
                if tool_calls:
                    continue
                return content.strip()
        if isinstance(content, list):
            texts = [
                block.get("text", "")
                for block in content
                if isinstance(block, dict) and block.get("type") == "text"
            ]
            joined = "\n".join(t for t in texts if t).strip()
            if joined:
                tool_calls = getattr(msg, "tool_calls", None)
                if tool_calls:
                    continue
                return joined
    return "도구 결과를 바탕으로 답을 만들지 못했습니다."


def run_agent_question(
    conn: kuzu.Connection,
    question: str,
    *,
    model: Any | None = None,
) -> AgentAskResponse:
    """Invoke create_agent with Kuzu tools and return answer + collected graph."""
    if model is None and not google_api_key():
        raise AgentUnavailableError(
            "GOOGLE_API_KEY is not set; cannot run LangChain agent"
        )

    from langchain.agents import create_agent

    collector = GraphCollector()
    tools = build_kuzu_tools(conn, collector)
    agent = create_agent(
        model=model or langchain_model(),
        tools=tools,
        system_prompt=SYSTEM_PROMPT,
    )
    result = agent.invoke({"messages": [{"role": "user", "content": question}]})
    answer = _extract_answer(result if isinstance(result, dict) else {"messages": []})
    # de-dupe tools_used preserving order
    seen: set[str] = set()
    tools_used: list[str] = []
    for name in collector.tools_used:
        if name not in seen:
            seen.add(name)
            tools_used.append(name)
    return AgentAskResponse(
        answer=answer,
        graph=collector.payload or GraphPayload(),
        tools_used=tools_used,
    )
