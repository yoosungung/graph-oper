"""Graph seed/expand queries against Kuzu."""

from __future__ import annotations

from typing import Any

import kuzu

from app.models import GraphEdge, GraphNode, GraphPayload, PersonHit

def _num(value: Any) -> int | float:
    v = _jsonable(value)
    if isinstance(v, bool):
        return int(v)
    if isinstance(v, int):
        return v
    if isinstance(v, float):
        return int(v) if v.is_integer() else v
    if isinstance(v, str):
        n = float(v) if "." in v else int(v)
        return int(n) if float(n).is_integer() else n
    raise TypeError(f"not a number: {value!r}")


def _jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    try:
        from decimal import Decimal

        if isinstance(value, Decimal):
            return float(value)
    except Exception:
        pass
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    return str(value)


def _rows(result: Any) -> list[list[Any]]:
    out: list[list[Any]] = []
    while result.has_next():
        out.append(result.get_next())
    return out


def node_id(label: str, pk: str) -> str:
    return f"{label}:{pk}"


def _person_node(pid: str, name: str, role: str) -> GraphNode:
    return GraphNode(
        id=node_id("Person", pid),
        label="Person",
        display=name or pid,
        props={"id": pid, "name": name, "role": role},
    )


def _phone_node(number: str, carrier: str | None = None) -> GraphNode:
    return GraphNode(
        id=node_id("Phone", number),
        label="Phone",
        display=number,
        props={"number": number, "carrier": carrier},
    )


def _account_node(
    account_id: str, bank: str | None = None, account_type: str | None = None
) -> GraphNode:
    return GraphNode(
        id=node_id("Account", account_id),
        label="Account",
        display=account_id,
        props={
            "account_id": account_id,
            "bank": bank,
            "account_type": account_type,
        },
    )


def merge_payload(*parts: GraphPayload) -> GraphPayload:
    nodes: dict[str, GraphNode] = {}
    edges: dict[str, GraphEdge] = {}
    for part in parts:
        for n in part.nodes:
            nodes[n.id] = n
        for e in part.edges:
            edges[e.id] = e
    return GraphPayload(nodes=list(nodes.values()), edges=list(edges.values()))


def search_persons(conn: kuzu.Connection, q: str, limit: int = 20) -> list[PersonHit]:
    result = conn.execute(
        """
        MATCH (p:Person)
        WHERE starts_with(p.id, $prefix) OR starts_with(p.name, $prefix)
        RETURN p.id, p.name, p.role
        ORDER BY p.id
        LIMIT $lim
        """,
        {"prefix": q, "lim": limit},
    )
    return [
        PersonHit(id=r[0], name=r[1], role=r[2] or "")
        for r in _rows(result)
    ]


def seed_person(conn: kuzu.Connection, person_id: str) -> GraphPayload:
    person_result = conn.execute(
        """
        MATCH (p:Person {id: $pid})
        RETURN p.id, p.name, p.role
        """,
        {"pid": person_id},
    )
    prow = _rows(person_result)
    if not prow:
        return GraphPayload()

    payload = GraphPayload(nodes=[_person_node(prow[0][0], prow[0][1], prow[0][2])])

    phones = conn.execute(
        """
        MATCH (p:Person {id: $pid})-[r:OwnsPhone]->(ph:Phone)
        RETURN ph.number, ph.carrier, r.since
        """,
        {"pid": person_id},
    )
    for number, carrier, since in _rows(phones):
        payload.nodes.append(_phone_node(number, carrier))
        payload.edges.append(
            GraphEdge(
                id=f"OwnsPhone:{person_id}:{number}",
                source=node_id("Person", person_id),
                target=node_id("Phone", number),
                rel="OwnsPhone",
                props={"since": since},
            )
        )

    accounts = conn.execute(
        """
        MATCH (p:Person {id: $pid})-[r:OwnsAccount]->(a:Account)
        RETURN a.account_id, a.bank, a.account_type
        """,
        {"pid": person_id},
    )
    for account_id, bank, account_type in _rows(accounts):
        payload.nodes.append(_account_node(account_id, bank, account_type))
        payload.edges.append(
            GraphEdge(
                id=f"OwnsAccount:{person_id}:{account_id}",
                source=node_id("Person", person_id),
                target=node_id("Account", account_id),
                rel="OwnsAccount",
                props={},
            )
        )

    return payload


def expand_node(conn: kuzu.Connection, pk: str, label: str) -> GraphPayload:
    if label == "Person":
        return seed_person(conn, pk)
    if label == "Phone":
        return _expand_phone(conn, pk)
    if label == "Account":
        return _expand_account(conn, pk)
    raise ValueError(f"unsupported label: {label}")


def _expand_phone(conn: kuzu.Connection, number: str) -> GraphPayload:
    phone_rows = _rows(
        conn.execute(
            "MATCH (ph:Phone {number: $n}) RETURN ph.number, ph.carrier",
            {"n": number},
        )
    )
    if not phone_rows:
        return GraphPayload()

    payload = GraphPayload(nodes=[_phone_node(phone_rows[0][0], phone_rows[0][1])])

    owners = conn.execute(
        """
        MATCH (p:Person)-[r:OwnsPhone]->(ph:Phone {number: $n})
        RETURN p.id, p.name, p.role, r.since
        """,
        {"n": number},
    )
    for pid, name, role, since in _rows(owners):
        payload.nodes.append(_person_node(pid, name, role))
        payload.edges.append(
            GraphEdge(
                id=f"OwnsPhone:{pid}:{number}",
                source=node_id("Person", pid),
                target=node_id("Phone", number),
                rel="OwnsPhone",
                props={"since": since},
            )
        )

    outgoing = conn.execute(
        """
        MATCH (a:Phone {number: $n})-[c:Called]->(b:Phone)
        RETURN b.number, b.carrier, count(c), sum(c.duration_sec)
        """,
        {"n": number},
    )
    incoming = conn.execute(
        """
        MATCH (a:Phone)-[c:Called]->(b:Phone {number: $n})
        RETURN a.number, a.carrier, count(c), sum(c.duration_sec)
        """,
        {"n": number},
    )
    for other_number, other_carrier, count, duration_sec in _rows(outgoing):
        payload.nodes.append(_phone_node(other_number, other_carrier))
        payload.edges.append(
            GraphEdge(
                id=f"Called:{number}:{other_number}",
                source=node_id("Phone", number),
                target=node_id("Phone", other_number),
                rel="Called",
                props={"count": _num(count), "duration_sec": _num(duration_sec)},
            )
        )
    for other_number, other_carrier, count, duration_sec in _rows(incoming):
        payload.nodes.append(_phone_node(other_number, other_carrier))
        payload.edges.append(
            GraphEdge(
                id=f"Called:{other_number}:{number}",
                source=node_id("Phone", other_number),
                target=node_id("Phone", number),
                rel="Called",
                props={"count": _num(count), "duration_sec": _num(duration_sec)},
            )
        )

    return payload


def _expand_account(conn: kuzu.Connection, account_id: str) -> GraphPayload:
    acc_rows = _rows(
        conn.execute(
            """
            MATCH (a:Account {account_id: $aid})
            RETURN a.account_id, a.bank, a.account_type
            """,
            {"aid": account_id},
        )
    )
    if not acc_rows:
        return GraphPayload()

    payload = GraphPayload(
        nodes=[_account_node(acc_rows[0][0], acc_rows[0][1], acc_rows[0][2])]
    )

    owners = conn.execute(
        """
        MATCH (p:Person)-[r:OwnsAccount]->(a:Account {account_id: $aid})
        RETURN p.id, p.name, p.role
        """,
        {"aid": account_id},
    )
    for pid, name, role in _rows(owners):
        payload.nodes.append(_person_node(pid, name, role))
        payload.edges.append(
            GraphEdge(
                id=f"OwnsAccount:{pid}:{account_id}",
                source=node_id("Person", pid),
                target=node_id("Account", account_id),
                rel="OwnsAccount",
                props={},
            )
        )

    outgoing = conn.execute(
        """
        MATCH (a:Account {account_id: $aid})-[t:Transferred]->(b:Account)
        RETURN b.account_id, b.bank, b.account_type, count(t), sum(t.amount)
        """,
        {"aid": account_id},
    )
    incoming = conn.execute(
        """
        MATCH (a:Account)-[t:Transferred]->(b:Account {account_id: $aid})
        RETURN a.account_id, a.bank, a.account_type, count(t), sum(t.amount)
        """,
        {"aid": account_id},
    )
    for other_id, other_bank, other_type, count, amount in _rows(outgoing):
        payload.nodes.append(_account_node(other_id, other_bank, other_type))
        payload.edges.append(
            GraphEdge(
                id=f"Transferred:{account_id}:{other_id}",
                source=node_id("Account", account_id),
                target=node_id("Account", other_id),
                rel="Transferred",
                props={"count": _num(count), "amount": _num(amount)},
            )
        )
    for other_id, other_bank, other_type, count, amount in _rows(incoming):
        payload.nodes.append(_account_node(other_id, other_bank, other_type))
        payload.edges.append(
            GraphEdge(
                id=f"Transferred:{other_id}:{account_id}",
                source=node_id("Account", other_id),
                target=node_id("Account", account_id),
                rel="Transferred",
                props={"count": _num(count), "amount": _num(amount)},
            )
        )

    return payload
