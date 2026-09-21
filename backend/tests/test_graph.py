from __future__ import annotations

import kuzu

from app.graph import expand_node, search_persons, seed_person


def test_seed_includes_owned_phone_and_account_only(conn: kuzu.Connection) -> None:
    payload = seed_person(conn, "김철수")
    node_ids = {n.id for n in payload.nodes}
    edge_rels = {e.rel for e in payload.edges}
    assert "Person:김철수" in node_ids
    assert "Phone:010-1111-0001" in node_ids
    assert "Account:110-111-0001" in node_ids
    assert "Phone:010-2222-0002" not in node_ids
    assert edge_rels == {"OwnsPhone", "OwnsAccount"}
    assert all(e.rel != "Called" for e in payload.edges)
    assert all(e.rel != "Transferred" for e in payload.edges)


def test_seed_missing_person(conn: kuzu.Connection) -> None:
    payload = seed_person(conn, "없는사람")
    assert payload.nodes == []
    assert payload.edges == []


def test_expand_phone_returns_calls_and_owner(conn: kuzu.Connection) -> None:
    payload = expand_node(conn, "010-1111-0001", "Phone")
    node_ids = {n.id for n in payload.nodes}
    edge_ids = {e.id for e in payload.edges}
    assert "Phone:010-1111-0001" in node_ids
    assert "Phone:010-2222-0002" in node_ids
    assert "Person:김철수" in node_ids
    assert "Called:010-1111-0001:010-2222-0002" in edge_ids
    assert "Called:c1" not in edge_ids
    called = next(e for e in payload.edges if e.rel == "Called")
    assert called.source == "Phone:010-1111-0001"
    assert called.target == "Phone:010-2222-0002"
    assert called.props == {"count": 1, "duration_sec": 60}
    assert "OwnsPhone:김철수:010-1111-0001" in edge_ids


def test_expand_account_returns_transfers_and_owner(conn: kuzu.Connection) -> None:
    payload = expand_node(conn, "110-111-0001", "Account")
    node_ids = {n.id for n in payload.nodes}
    edge_ids = {e.id for e in payload.edges}
    assert "Account:110-222-0002" in node_ids
    assert "Person:김철수" in node_ids
    assert "Transferred:110-111-0001:110-222-0002" in edge_ids
    assert "Transferred:t1" not in edge_ids
    transferred = next(e for e in payload.edges if e.rel == "Transferred")
    assert transferred.source == "Account:110-111-0001"
    assert transferred.target == "Account:110-222-0002"
    assert transferred.props == {"count": 1, "amount": 1000000}


def test_expand_phone_sums_calls_per_direction(conn: kuzu.Connection) -> None:
    conn.execute(
        """
        MATCH (a:Phone {number: '010-1111-0001'}), (b:Phone {number: '010-2222-0002'})
        CREATE (a)-[:Called {
            call_id: 'c2', started_at: '2024-06-03T10:00:00', ended_at: '',
            duration_sec: 90, call_type: '음성', company: '', location: '',
            end_location: '', note1: '', note2: ''
        }]->(b)
        """
    )
    conn.execute(
        """
        MATCH (a:Phone {number: '010-2222-0002'}), (b:Phone {number: '010-1111-0001'})
        CREATE (a)-[:Called {
            call_id: 'c3', started_at: '2024-06-04T10:00:00', ended_at: '',
            duration_sec: 30, call_type: '음성', company: '', location: '',
            end_location: '', note1: '', note2: ''
        }]->(b)
        """
    )
    payload = expand_node(conn, "010-1111-0001", "Phone")
    calls = {e.id: e for e in payload.edges if e.rel == "Called"}
    assert set(calls) == {
        "Called:010-1111-0001:010-2222-0002",
        "Called:010-2222-0002:010-1111-0001",
    }
    assert calls["Called:010-1111-0001:010-2222-0002"].props == {
        "count": 2,
        "duration_sec": 150,
    }
    assert calls["Called:010-2222-0002:010-1111-0001"].props == {
        "count": 1,
        "duration_sec": 30,
    }
    other = expand_node(conn, "010-2222-0002", "Phone")
    assert {e.id for e in other.edges if e.rel == "Called"} == set(calls)


def test_expand_account_sums_transfers_per_direction(conn: kuzu.Connection) -> None:
    conn.execute(
        """
        MATCH (a:Account {account_id: '110-111-0001'}), (b:Account {account_id: '110-222-0002'})
        CREATE (a)-[:Transferred {
            tx_id: 't2', amount: 500000.0, transferred_at: '2024-06-03T12:00:00',
            memo: '', direction: '출금', tx_type: '이체', branch: '',
            balance_after: 0.0, terminal: '', ip: '', mac: '', note1: '', note2: ''
        }]->(b)
        """
    )
    conn.execute(
        """
        MATCH (a:Account {account_id: '110-222-0002'}), (b:Account {account_id: '110-111-0001'})
        CREATE (a)-[:Transferred {
            tx_id: 't3', amount: 20000.0, transferred_at: '2024-06-04T12:00:00',
            memo: '', direction: '출금', tx_type: '이체', branch: '',
            balance_after: 0.0, terminal: '', ip: '', mac: '', note1: '', note2: ''
        }]->(b)
        """
    )
    payload = expand_node(conn, "110-111-0001", "Account")
    txs = {e.id: e for e in payload.edges if e.rel == "Transferred"}
    assert txs["Transferred:110-111-0001:110-222-0002"].props == {
        "count": 2,
        "amount": 1500000,
    }
    assert txs["Transferred:110-222-0002:110-111-0001"].props == {
        "count": 1,
        "amount": 20000,
    }


def test_search_persons_prefix(conn: kuzu.Connection) -> None:
    hits = search_persons(conn, "김")
    assert any(h.id == "김철수" for h in hits)
