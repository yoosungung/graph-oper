"""Pydantic models for GraphPayload."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class GraphNode(BaseModel):
    id: str
    label: str
    display: str
    props: dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    rel: str
    props: dict[str, Any] = Field(default_factory=dict)


class GraphPayload(BaseModel):
    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)


class PersonHit(BaseModel):
    id: str
    name: str
    role: str


class AgentAskRequest(BaseModel):
    question: str = Field(..., min_length=1)


class AgentAskResponse(BaseModel):
    answer: str
    graph: GraphPayload = Field(default_factory=GraphPayload)
    tools_used: list[str] = Field(default_factory=list)
