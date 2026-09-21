# graph-oper

경찰 사건 통화·이체 그래프를 Kuzu에 올리고, FastAPI + Cytoscape.js로 인터랙티브하게 탐색합니다.

- 계약·API: [ARCHITECTURE.md](ARCHITECTURE.md)
- 일정: [ROADMAP.md](ROADMAP.md)
- 에이전트 가이드: [AGENTS.md](AGENTS.md)
- 데이터/분석 패키지: [police-case-kuzu/README.md](police-case-kuzu/README.md)
- 백엔드: [backend/DESIGN.md](backend/DESIGN.md)
- 프론트엔드: [frontend/DESIGN.md](frontend/DESIGN.md)

## Quickstart

### 1. 샘플 DB

```bash
cd police-case-kuzu
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=src python scripts/generate_sample_data.py --size 2000 --out data
PYTHONPATH=src python scripts/load_sample_db.py   # → sample.db
```

### 2. Backend

Python **3.10+** 필요 (LangChain `create_agent`, 권장 3.12).

```bash
cd backend
# 예: uv venv --python 3.12 .venv && source .venv/bin/activate
pip install -r requirements.txt
# backend/.env 에 GOOGLE_API_KEY 를 채운 뒤
uvicorn app.main:app --reload --port 8000 --env-file .env
```

VS Code/Cursor에서는 **Run and Debug → `backend + frontend`** 로 두 서버를 같이 띄운다. 키는 `backend/.env`만 사용한다.

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

브라우저에서 Vite URL(기본 `http://localhost:5173`)을 연 뒤 인물(예: `김철수`)을 시드하거나, 자연어 질문으로 agent가 그래프를 채우게 합니다.
