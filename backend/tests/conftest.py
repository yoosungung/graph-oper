from __future__ import annotations

import importlib.util
from pathlib import Path

import kuzu
import pytest


def _load_create_schema():
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


create_schema = _load_create_schema()


@pytest.fixture
def conn(tmp_path: Path) -> kuzu.Connection:
    db = kuzu.Database(str(tmp_path / "test.db"))
    connection = kuzu.Connection(db)
    create_schema(connection)
    connection.execute(
        "CREATE (:Person {id: '김철수', name: '김철수', role: '두목'})"
    )
    connection.execute(
        "CREATE (:Person {id: '이영희', name: '이영희', role: 'gate-keeper'})"
    )
    connection.execute(
        "CREATE (:Phone {number: '010-1111-0001', carrier: 'KT'})"
    )
    connection.execute(
        "CREATE (:Phone {number: '010-2222-0002', carrier: 'SK'})"
    )
    connection.execute(
        "CREATE (:Account {account_id: '110-111-0001', bank: 'KB', account_type: '보통'})"
    )
    connection.execute(
        "CREATE (:Account {account_id: '110-222-0002', bank: 'KB', account_type: '보통'})"
    )
    connection.execute(
        """
        MATCH (p:Person {id: '김철수'}), (ph:Phone {number: '010-1111-0001'})
        CREATE (p)-[:OwnsPhone {since: '2024-01-01'}]->(ph)
        """
    )
    connection.execute(
        """
        MATCH (p:Person {id: '김철수'}), (a:Account {account_id: '110-111-0001'})
        CREATE (p)-[:OwnsAccount]->(a)
        """
    )
    connection.execute(
        """
        MATCH (p:Person {id: '이영희'}), (ph:Phone {number: '010-2222-0002'})
        CREATE (p)-[:OwnsPhone {since: '2024-01-01'}]->(ph)
        """
    )
    connection.execute(
        """
        MATCH (p:Person {id: '이영희'}), (a:Account {account_id: '110-222-0002'})
        CREATE (p)-[:OwnsAccount]->(a)
        """
    )
    connection.execute(
        """
        MATCH (a:Phone {number: '010-1111-0001'}), (b:Phone {number: '010-2222-0002'})
        CREATE (a)-[:Called {
            call_id: 'c1',
            started_at: '2024-06-01T10:00:00',
            ended_at: '2024-06-01T10:01:00',
            duration_sec: 60,
            call_type: '음성',
            company: '',
            location: '',
            end_location: '',
            note1: '',
            note2: ''
        }]->(b)
        """
    )
    connection.execute(
        """
        MATCH (a:Account {account_id: '110-111-0001'}), (b:Account {account_id: '110-222-0002'})
        CREATE (a)-[:Transferred {
            tx_id: 't1',
            amount: 1000000.0,
            transferred_at: '2024-06-02T12:00:00',
            memo: '상납',
            direction: '출금',
            tx_type: '이체',
            branch: '',
            balance_after: 0.0,
            terminal: '',
            ip: '',
            mac: '',
            note1: '',
            note2: ''
        }]->(b)
        """
    )
    return connection
