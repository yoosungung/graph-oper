import { useCallback, useEffect, useState } from "react";
import {
  askAgent,
  fetchHealth,
  searchPersons,
  seedGraph,
  type GraphPayload,
  type PersonHit,
} from "./api";
import GraphView from "./GraphView";
import "./App.css";

export default function App() {
  const [query, setQuery] = useState("김철수");
  const [hits, setHits] = useState<PersonHit[]>([]);
  const [seed, setSeed] = useState<GraphPayload | null>(null);
  const [selected, setSelected] = useState<Record<string, unknown> | null>(
    null,
  );
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [expanding, setExpanding] = useState(false);
  const [healthOk, setHealthOk] = useState<boolean | null>(null);
  const [nlQuestion, setNlQuestion] = useState(
    "김철수의 전화와 계좌, 통화 상대를 보여줘",
  );
  const [answer, setAnswer] = useState<string | null>(null);
  const [asking, setAsking] = useState(false);
  const [toolsUsed, setToolsUsed] = useState<string[]>([]);

  useEffect(() => {
    fetchHealth()
      .then((h) => {
        setHealthOk(h.ok);
        if (!h.ok) setError(h.error ?? "DB unavailable");
      })
      .catch((err: Error) => {
        setHealthOk(false);
        setError(err.message);
      });
  }, []);

  useEffect(() => {
    if (query.trim().length < 1) {
      setHits([]);
      return;
    }
    const t = window.setTimeout(() => {
      searchPersons(query.trim())
        .then(setHits)
        .catch(() => setHits([]));
    }, 200);
    return () => window.clearTimeout(t);
  }, [query]);

  const loadSeed = useCallback(async (personId: string) => {
    setError(null);
    setStatus(`시드 로드: ${personId}`);
    try {
      const payload = await seedGraph(personId);
      setSeed(payload);
      setAnswer(null);
      setToolsUsed([]);
      setStatus(
        `시드 ${payload.nodes.length} nodes / ${payload.edges.length} edges — 노드 더블클릭으로 확장`,
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "seed 실패");
      setStatus(null);
    }
  }, []);

  const runAgent = useCallback(async (question: string) => {
    setAsking(true);
    setError(null);
    setStatus("Agent 조회 중…");
    try {
      const res = await askAgent(question);
      setAnswer(res.answer);
      setToolsUsed(res.tools_used);
      setSeed(res.graph);
      setStatus(
        `agent graph ${res.graph.nodes.length} nodes / ${res.graph.edges.length} edges`,
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "agent 실패");
      setStatus(null);
    } finally {
      setAsking(false);
    }
  }, []);

  const onStatus = useCallback((message: string | null, isError?: boolean) => {
    if (isError) {
      setError(message);
      return;
    }
    setError(null);
    setStatus(message);
  }, []);

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark">graph-oper</span>
          <span className="brand-sub">Kuzu · Cytoscape · Agent</span>
        </div>
        <form
          className="seed-form"
          onSubmit={(e) => {
            e.preventDefault();
            void loadSeed(query.trim());
          }}
        >
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="인물 id / 이름"
            aria-label="인물 검색"
            list="person-hits"
          />
          <datalist id="person-hits">
            {hits.map((h) => (
              <option key={h.id} value={h.id}>
                {h.name} ({h.role})
              </option>
            ))}
          </datalist>
          <button type="submit">시드</button>
        </form>
        <div
          className={`health ${healthOk === false ? "bad" : healthOk ? "ok" : ""}`}
        >
          {healthOk === null ? "…" : healthOk ? "DB OK" : "DB DOWN"}
        </div>
      </header>

      <form
        className="agent-bar"
        onSubmit={(e) => {
          e.preventDefault();
          void runAgent(nlQuestion.trim());
        }}
      >
        <input
          value={nlQuestion}
          onChange={(e) => setNlQuestion(e.target.value)}
          placeholder="자연어로 그래프 질문…"
          aria-label="자연어 질문"
          disabled={asking}
        />
        <button type="submit" disabled={asking || !nlQuestion.trim()}>
          {asking ? "조회 중…" : "Agent"}
        </button>
      </form>

      <main className="main">
        <GraphView
          seed={seed}
          onSelect={setSelected}
          onStatus={onStatus}
          onExpanding={setExpanding}
        />
        <aside className="side">
          <h2>Agent 답변</h2>
          {answer ? (
            <p className="answer">{answer}</p>
          ) : (
            <p className="hint">자연어 질문 시 답변이 여기에 표시됩니다.</p>
          )}
          {toolsUsed.length > 0 && (
            <p className="tools">tools: {toolsUsed.join(", ")}</p>
          )}

          <h2>선택</h2>
          {selected ? (
            <pre>{JSON.stringify(selected, null, 2)}</pre>
          ) : (
            <p className="hint">노드를 클릭하면 속성이 표시됩니다.</p>
          )}
          <h2>안내</h2>
          <ul className="hint-list">
            <li>시드: Person + 소유 Phone/Account</li>
            <li>Agent: 자연어 → Kuzu tools → 답변+그래프</li>
            <li>더블클릭: 1홉 이웃 확장 (통화·이체는 방향별 합산)</li>
            <li>드래그: 1홉을 당긴 뒤 놓으면 전체가 펴짐</li>
          </ul>
          {(status || expanding) && (
            <p className="status">
              {expanding ? "확장 중… " : ""}
              {status}
            </p>
          )}
          {error && <p className="error">{error}</p>}
        </aside>
      </main>
    </div>
  );
}
