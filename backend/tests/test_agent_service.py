from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import kuzu
import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from app.agent_service import AgentUnavailableError, _extract_answer, run_agent_question


def test_extract_answer_prefers_final_ai_text() -> None:
    result = {
        "messages": [
            HumanMessage(content="q"),
            AIMessage(content="", tool_calls=[{"name": "x", "args": {}, "id": "1"}]),
            ToolMessage(content="{}", tool_call_id="1"),
            AIMessage(content="김철수는 전화 2대를 소유합니다."),
        ]
    }
    assert "김철수" in _extract_answer(result)


def test_run_agent_requires_api_key(
    conn: kuzu.Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(AgentUnavailableError):
        run_agent_question(conn, "김철수 보여줘")


def test_run_agent_with_mocked_create_agent(
    conn: kuzu.Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")

    def fake_create_agent(**kwargs: Any) -> Any:
        tools = kwargs["tools"]
        agent = MagicMock()

        def _invoke(_payload: dict[str, Any]) -> dict[str, Any]:
            for t in tools:
                if t.name == "seed_person_tool":
                    t.invoke({"person_id": "김철수"})
            return {
                "messages": [
                    HumanMessage(content="김철수 보여줘"),
                    AIMessage(content="김철수와 소유 전화·계좌를 불러왔습니다."),
                ]
            }

        agent.invoke.side_effect = _invoke
        return agent

    monkeypatch.setattr("langchain.agents.create_agent", fake_create_agent)
    resp = run_agent_question(conn, "김철수 보여줘")
    assert "김철수" in resp.answer
    assert any(n.id == "Person:김철수" for n in resp.graph.nodes)
    assert "seed_person" in resp.tools_used
