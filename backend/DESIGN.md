# backend DESIGN

FastAPI가 임베디드 Kuzu로 `sample.db`를 조회해 GraphPayload를 반환한다. 계약은 [ARCHITECTURE.md](../ARCHITECTURE.md).

## 내부 구조

```
backend/
  app/
    main.py          # FastAPI lifespan, 라우트
    config.py        # KUZU_DB_PATH, LLM 모델
    db.py            # Database/Connection 수명
    graph.py         # seed / expand / persons 쿼리 + 정규화
    models.py        # Pydantic GraphPayload / AgentAsk*
    agent_tools.py   # Kuzu tool + GraphCollector
    agent_service.py # langchain.agents.create_agent
  tests/
  requirements.txt
```

- `police_graph` 패키지: 스키마 생성은 테스트 fixture에서만 사용. 런타임 조회는 `app/graph.py`에 둔다.
- 연결은 프로세스당 1회 lifespan에서 연다.
- Agent는 `create_agent(model=..., tools=[...])`로 구성한다. tool 호출 결과가 GraphCollector에 merge되고, 최종 `answer`는 모델 메시지다.

## Commands

```bash
cd backend
# LangChain create_agent 는 Python 3.10+ 필요 (권장 3.12)
# uv 예: uv venv --python 3.12 .venv && source .venv/bin/activate
python3 -m venv .venv && source .venv/bin/activate   # 3.10+ 인 경우
pip install -r requirements.txt

pytest -q

# 서버 (기본 DB: ../police-case-kuzu/sample.db)
# 키는 backend/.env (gitignore). VS Code Run and Debug: "backend + frontend"
uvicorn app.main:app --reload --port 8000 --env-file .env
```

환경변수 (`backend/.env`):
- `KUZU_DB_PATH` — 비우면 `../police-case-kuzu/sample.db`
- `GOOGLE_API_KEY` — Google AI Studio Gemini API 키 (또는 `GEMINI_API_KEY`)
- `LANGCHAIN_MODEL` — 비우면 `google_genai:gemma-4-31b-it`
