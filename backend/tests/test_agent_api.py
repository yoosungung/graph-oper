from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import kuzu
import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, HumanMessage


def _load_create_schema():
    import importlib.util

    schema_path = (
        Path(__file__).resolve().parents[2]
        / "police-case-kuzu"
        / "src"
        / "police_graph"
        / "schema.py"
    )
    spec = importlib.util.spec_from_file_location("police_schema", schema_path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.create_schema


@pytest.fixture
def agent_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_path = tmp_path / "agent.db"
    db = kuzu.Database(str(db_path))
    conn = kuzu.Connection(db)
    _load_create_schema()(conn)
    conn.execute("CREATE (:Person {id: '김철수', name: '김철수', role: '두목'})")
    conn.execute("CREATE (:Phone {number: '010-1111-0001', carrier: 'KT'})")
    conn.execute(
        """
        MATCH (p:Person {id: '김철수'}), (ph:Phone {number: '010-1111-0001'})
        CREATE (p)-[:OwnsPhone {since: '2024-01-01'}]->(ph)
        """
    )
    del conn
    del db
    monkeypatch.setenv("KUZU_DB_PATH", str(db_path))
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    return db_path


def test_agent_ask_endpoint(agent_db: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_create_agent(**kwargs):
        tools = kwargs["tools"]
        agent = MagicMock()

        def _invoke(_payload):
            for t in tools:
                if t.name == "seed_person_tool":
                    t.invoke({"person_id": "김철수"})
            return {
                "messages": [
                    HumanMessage(content="q"),
                    AIMessage(content="그래프를 준비했습니다."),
                ]
            }

        agent.invoke.side_effect = _invoke
        return agent

    monkeypatch.setattr("langchain.agents.create_agent", fake_create_agent)

    from app.main import app

    with TestClient(app) as client:
        res = client.post("/api/agent/ask", json={"question": "김철수 보여줘"})
        assert res.status_code == 200
        body = res.json()
        assert "그래프" in body["answer"]
        assert any(n["id"] == "Person:김철수" for n in body["graph"]["nodes"])
        assert "seed_person" in body["tools_used"]
