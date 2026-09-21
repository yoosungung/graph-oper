# ARCHITECTURE

컴포넌트 *간* 계약과 인터페이스 형태. 내부 설계는 `backend/DESIGN.md`, `frontend/DESIGN.md`.

## 1. 계약사항

- 그래프 UI는 **전체 그래프를 한 번에 로드하지 않는다.** seed → 1홉 expand로만 확장한다.
- expand는 항상 **선택한 노드의 1홉**만 반환한다.
- 노드 안정 id는 `{label}:{primary_key}` 형식이다 (`Person:김철수`, `Phone:010-...`, `Account:110-...`).
- 소유 엣지 id는 `OwnsPhone:{person}:{number}`, `OwnsAccount:{person}:{account}` 다.
- expand의 Called/Transferred는 방향(출발→도착)당 엣지 하나다. id는 `Called:{from}:{to}`, `Transferred:{from}:{to}`. props는 통화 `count`·`duration_sec`, 이체 `count`·`amount`. 건별 기록은 DB에 남긴다.
- Kuzu는 **FastAPI 프로세스 안**에서만 연다. 브라우저는 REST만 호출한다.
- 데이터 원천은 `police-case-kuzu/sample.db`(또는 `KUZU_DB_PATH`). 스키마 정본은 `police-case-kuzu`.
- 자연어 질의는 backend의 LangChain `create_agent`가 **허용된 Kuzu tool만** 호출한다. 임의 Cypher 문자열 실행은 허용하지 않는다.
- Agent 응답은 항상 `{ answer, graph }`다. `graph`는 기존 GraphPayload이며 frontend GraphView에 그대로 넣는다.

## 2. 컴포넌트

| 컴포넌트 | 역할 |
|----------|------|
| `police-case-kuzu` | 스키마·CSV 적재·분석 CLI·`sample.db` |
| `backend` | FastAPI + 임베디드 Kuzu 조회 API |
| `frontend` | React + Cytoscape.js 인터랙티브 그래프 |

## 3. GraphPayload (REST 공통)

```json
{
  "nodes": [
    {
      "id": "Person:김철수",
      "label": "Person",
      "display": "김철수",
      "props": { "name": "김철수", "role": "두목" }
    }
  ],
  "edges": [
    {
      "id": "OwnsPhone:김철수:010-1111-0001",
      "source": "Person:김철수",
      "target": "Phone:010-1111-0001",
      "rel": "OwnsPhone",
      "props": { "since": "..." }
    }
  ]
}
```

- `nodes[].label`: `Person` | `Phone` | `Account`
- `edges[].rel`: `OwnsPhone` | `OwnsAccount` | `Called` | `Transferred`

## 4. REST 엔드포인트

| Method | Path | 설명 |
|--------|------|------|
| `GET` | `/api/health` | DB 연결 상태 |
| `GET` | `/api/persons?q=` | 인물 id/name prefix 검색 |
| `GET` | `/api/graph/seed?person_id=` | Person + 소유 Phone/Account (1홉 소유만) |
| `GET` | `/api/graph/expand?id=&label=` | 해당 노드 1홉 이웃·관계 |
| `POST` | `/api/agent/ask` | 자연어 → agent tool → `{ answer, graph }` |

### agent ask

요청:

```json
{ "question": "김철수의 통화 상대와 연결된 번호를 보여줘" }
```

응답:

```json
{
  "answer": "김철수 소유 전화 010-... 에서 ...",
  "graph": { "nodes": [], "edges": [] },
  "tools_used": ["search_persons", "seed_person", "expand_node"]
}
```

- Agent tool은 `search_persons` / `seed_person` / `expand_node` 만 사용한다 (ARCHITECTURE §1).
- tool이 반환·수집한 GraphPayload를 합쳐 `graph`로 내려보낸다.
- LLM 미설정(`GOOGLE_API_KEY` 등)이면 `503`.

### seed

- 입력: `person_id` (Person.id)
- 출력: 해당 Person, `OwnsPhone`/`OwnsAccount` 엣지, 연결된 Phone/Account
- Called / Transferred는 seed에 포함하지 않는다

### expand

- 입력: `id`(primary key 값), `label` (`Person`|`Phone`|`Account`)
- 출력: 그 노드에서 나가는/들어오는 **1홉** 전부
  - Person → OwnsPhone, OwnsAccount (+ 이웃 노드)
  - Phone → OwnsPhone, Called (+ 이웃). Called는 §1 합산 엣지
  - Account → OwnsAccount, Transferred (+ 이웃). Transferred는 §1 합산 엣지

클라이언트가 이미 가진 element id는 무시하고 신규만 `cy.add`한다.
