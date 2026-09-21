# frontend DESIGN

React + Cytoscape.js로 seed/expand GraphPayload를 병합 렌더한다. 계약은 [ARCHITECTURE.md](../ARCHITECTURE.md).

## 내부 구조

```
frontend/
  src/
    App.tsx           # 시드 입력, 자연어 질문, 패널
    api.ts            # /api/* fetch (agent/ask 포함)
    GraphView.tsx     # Cytoscape 인스턴스, 더블클릭 expand, 드래그 후 전체 이완
    fcoseOptions.ts   # 시드·확장·드롭 이완용 fCoSE 옵션
    dragNeighbors.ts  # 드래그 시 이웃 이동량, 이완 최소 거리
    durationLabel.ts  # 통화시간 초 → 분 라벨
    amountLabel.ts    # 거래금액 원 → 만원 라벨
    styles.ts         # 노드/엣지 stylesheet
  vite.config.ts      # /api → localhost:8000 proxy
```

- 노드 더블클릭 → `GET /api/graph/expand` → 기존 id skip 후 `cy.add` → fCoSE 레이아웃.
- 노드를 끌면 1홉 이웃만 이동의 55%만큼 따라온다. 8px 이상 옮긴 뒤 놓으면 그래프 전체를 fCoSE로 다시 펴고, 놓은 노드는 `fixedNodeConstraint`로 그 자리에 남는다. 시드·확장 배치도 fCoSE다.
- 자연어 질문 → `POST /api/agent/ask` → `answer` 사이드바 표시 + `graph`를 GraphView 시드로 교체.
- Person / Phone / Account 색·모양 구분.
- Called/Transferred 라벨은 방향별 합산 `count`와 량을 표시한다. 통화 량은 `duration_sec`을 분(소수 1자리)으로, 이체는 `amount`를 만원(소수 1자리)으로 보여 준다.
- 그 엣지 두께는 `log10(횟수 × 량)`을 1.2–8로 맞춘다. 량은 통화 `duration_sec`, 이체 `amount`. 소유 엣지는 1.2로 고정한다.

## Commands

```bash
cd frontend
npm install
npm run dev      # http://localhost:5173
npm run build
node --experimental-strip-types --test src/edgeWidth.test.ts src/durationLabel.test.ts src/amountLabel.test.ts src/dragNeighbors.test.ts src/fcoseOptions.test.ts
```
