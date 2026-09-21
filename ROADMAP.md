# ROADMAP

## 완료 / 진행 중

1. **경찰 사건 Kuzu 패키지** (`police-case-kuzu`) — 스키마·샘플 CSV·분석 CLI
2. **인터랙티브 그래프 UI** — FastAPI seed/expand + React Cytoscape.js
3. **자연어 Agent** — LangChain `create_agent` + Kuzu tools → answer + graph

## 다음 후보

- expand 시 관계 타입 필터 (Called만 / Transferred만)
- 선택 노드 사이 최단 경로 하이라이트
- 배포 런북 (`deploy/SETUP.md`) — 필요할 때 작성 (빈 stub 금지)

## 미결정

- 프로덕션 DB 경로·읽기 전용 마운트 방식
- 인증·접근통제 (수사 데이터 전제)
