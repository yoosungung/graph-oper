"""FastAPI app: Kuzu graph seed/expand."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware

from app.agent_service import AgentUnavailableError, run_agent_question
from app.config import db_path, google_api_key
from app.db import open_db
from app.graph import expand_node, search_persons, seed_person
from app.models import (
    AgentAskRequest,
    AgentAskResponse,
    GraphPayload,
    PersonHit,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    path = db_path()
    try:
        db, conn = open_db(path)
    except FileNotFoundError as exc:
        app.state.db = None
        app.state.conn = None
        app.state.db_error = str(exc)
        yield
        return
    app.state.db = db
    app.state.conn = conn
    app.state.db_error = None
    yield
    # Kuzu cleans up on GC; no explicit close required


app = FastAPI(title="graph-oper", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _conn(request: Request) -> Any:
    conn = request.app.state.conn
    if conn is None:
        raise HTTPException(
            status_code=503,
            detail=request.app.state.db_error or "Kuzu DB unavailable",
        )
    return conn


@app.get("/api/health")
def health(request: Request) -> dict[str, Any]:
    ok = request.app.state.conn is not None
    return {
        "ok": ok,
        "db_path": str(db_path()),
        "error": request.app.state.db_error,
        "agent_ready": bool(google_api_key()),
    }


@app.get("/api/persons", response_model=list[PersonHit])
def persons(
    request: Request,
    q: str = Query("", min_length=0),
    limit: int = Query(20, ge=1, le=100),
) -> list[PersonHit]:
    if not q:
        return []
    return search_persons(_conn(request), q, limit)


@app.get("/api/graph/seed", response_model=GraphPayload)
def graph_seed(
    request: Request,
    person_id: str = Query(..., min_length=1),
) -> GraphPayload:
    payload = seed_person(_conn(request), person_id)
    if not payload.nodes:
        raise HTTPException(status_code=404, detail=f"person not found: {person_id}")
    return payload


@app.get("/api/graph/expand", response_model=GraphPayload)
def graph_expand(
    request: Request,
    id: str = Query(..., min_length=1, alias="id"),
    label: str = Query(..., min_length=1),
) -> GraphPayload:
    if label not in {"Person", "Phone", "Account"}:
        raise HTTPException(status_code=400, detail=f"unsupported label: {label}")
    try:
        payload = expand_node(_conn(request), id, label)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not payload.nodes:
        raise HTTPException(status_code=404, detail=f"node not found: {label}:{id}")
    return payload


@app.post("/api/agent/ask", response_model=AgentAskResponse)
def agent_ask(request: Request, body: AgentAskRequest) -> AgentAskResponse:
    try:
        return run_agent_question(_conn(request), body.question)
    except AgentUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 — surface LLM/tool failures
        raise HTTPException(status_code=500, detail=str(exc)) from exc
