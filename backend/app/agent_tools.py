"""LangChain tools backed by Kuzu graph queries."""

from __future__ import annotations

import json
from dataclasses import dataclass, field

import kuzu
from langchain.tools import tool

from app.graph import expand_node, merge_payload, search_persons, seed_person
from app.models import GraphPayload


@dataclass
class GraphCollector:
    """Accumulates GraphPayload fragments produced by tools."""

    payload: GraphPayload = field(default_factory=GraphPayload)
    tools_used: list[str] = field(default_factory=list)

    def merge(self, fragment: GraphPayload, tool_name: str) -> None:
        self.payload = merge_payload(self.payload, fragment)
        self.tools_used.append(tool_name)


def build_kuzu_tools(conn: kuzu.Connection, collector: GraphCollector) -> list:
    """Create bound tools that query Kuzu and fill the collector."""

    @tool
    def search_persons_tool(query: str) -> str:
        """Search persons by id/name prefix. Use to resolve a Korean name to person_id."""
        hits = search_persons(conn, query, limit=10)
        collector.tools_used.append("search_persons")
        return json.dumps(
            [{"id": h.id, "name": h.name, "role": h.role} for h in hits],
            ensure_ascii=False,
        )

    @tool
    def seed_person_tool(person_id: str) -> str:
        """Load a Person and owned Phone/Account nodes (1-hop ownership only)."""
        fragment = seed_person(conn, person_id)
        collector.merge(fragment, "seed_person")
        if not fragment.nodes:
            return json.dumps({"ok": False, "error": f"person not found: {person_id}"})
        return json.dumps(
            {
                "ok": True,
                "node_count": len(fragment.nodes),
                "edge_count": len(fragment.edges),
                "node_ids": [n.id for n in fragment.nodes],
            },
            ensure_ascii=False,
        )

    @tool
    def expand_node_tool(node_pk: str, label: str) -> str:
        """Expand one hop from a node. label must be Person, Phone, or Account.
        node_pk is the primary key only (e.g. 김철수, 010-1100-1000), not Label:pk.
        """
        if label not in {"Person", "Phone", "Account"}:
            return json.dumps({"ok": False, "error": f"unsupported label: {label}"})
        fragment = expand_node(conn, node_pk, label)
        collector.merge(fragment, "expand_node")
        if not fragment.nodes:
            return json.dumps(
                {"ok": False, "error": f"node not found: {label}:{node_pk}"}
            )
        return json.dumps(
            {
                "ok": True,
                "node_count": len(fragment.nodes),
                "edge_count": len(fragment.edges),
                "rels": sorted({e.rel for e in fragment.edges}),
                "node_ids": [n.id for n in fragment.nodes][:30],
            },
            ensure_ascii=False,
        )

    return [search_persons_tool, seed_person_tool, expand_node_tool]
