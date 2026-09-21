from __future__ import annotations

import json

import kuzu

from app.agent_tools import GraphCollector, build_kuzu_tools
from app.graph import merge_payload
from app.models import GraphNode, GraphPayload


def test_merge_payload_dedupes() -> None:
    a = GraphPayload(
        nodes=[
            GraphNode(id="Person:A", label="Person", display="A", props={}),
        ]
    )
    b = GraphPayload(
        nodes=[
            GraphNode(id="Person:A", label="Person", display="A", props={"role": "x"}),
            GraphNode(id="Phone:1", label="Phone", display="1", props={}),
        ]
    )
    merged = merge_payload(a, b)
    assert {n.id for n in merged.nodes} == {"Person:A", "Phone:1"}
    assert next(n for n in merged.nodes if n.id == "Person:A").props["role"] == "x"


def test_tools_collect_graph(conn: kuzu.Connection) -> None:
    collector = GraphCollector()
    tools = {t.name: t for t in build_kuzu_tools(conn, collector)}

    search = tools["search_persons_tool"].invoke({"query": "김"})
    hits = json.loads(search)
    assert any(h["id"] == "김철수" for h in hits)
    assert "search_persons" in collector.tools_used

    seeded = json.loads(tools["seed_person_tool"].invoke({"person_id": "김철수"}))
    assert seeded["ok"] is True
    assert any(n.id == "Person:김철수" for n in collector.payload.nodes)
    assert any(n.label == "Phone" for n in collector.payload.nodes)

    phone = next(n for n in collector.payload.nodes if n.label == "Phone")
    pk = phone.props["number"]
    expanded = json.loads(
        tools["expand_node_tool"].invoke({"node_pk": pk, "label": "Phone"})
    )
    assert expanded["ok"] is True
    assert "Called" in expanded["rels"] or "OwnsPhone" in expanded["rels"]
    assert "expand_node" in collector.tools_used
