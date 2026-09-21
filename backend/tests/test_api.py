from __future__ import annotations

import importlib.util
from pathlib import Path

import kuzu
import pytest
from fastapi.testclient import TestClient


def _create_schema(conn: kuzu.Connection) -> None:
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
    mod.create_schema(conn)


@pytest.fixture
def sample_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_path = tmp_path / "api.db"
    db = kuzu.Database(str(db_path))
    conn = kuzu.Connection(db)
    _create_schema(conn)
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
    return db_path


def test_health_and_seed(sample_db: Path) -> None:
    from app.main import app

    with TestClient(app) as client:
        health = client.get("/api/health")
        assert health.status_code == 200
        assert health.json()["ok"] is True

        seed = client.get("/api/graph/seed", params={"person_id": "김철수"})
        assert seed.status_code == 200
        body = seed.json()
        assert any(n["id"] == "Person:김철수" for n in body["nodes"])
        assert any(n["label"] == "Phone" for n in body["nodes"])

        missing = client.get("/api/graph/seed", params={"person_id": "없음"})
        assert missing.status_code == 404

        expand = client.get(
            "/api/graph/expand",
            params={"id": "010-1111-0001", "label": "Phone"},
        )
        assert expand.status_code == 200
        assert any(n["id"] == "Person:김철수" for n in expand.json()["nodes"])
