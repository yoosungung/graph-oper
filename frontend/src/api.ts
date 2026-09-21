export type GraphNode = {
  id: string;
  label: string;
  display: string;
  props: Record<string, unknown>;
};

export type GraphEdge = {
  id: string;
  source: string;
  target: string;
  rel: string;
  props: Record<string, unknown>;
};

export type GraphPayload = {
  nodes: GraphNode[];
  edges: GraphEdge[];
};

export type PersonHit = {
  id: string;
  name: string;
  role: string;
};

async function readJson<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = (await res.json()) as { detail?: string };
      if (body.detail) detail = body.detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

export async function fetchHealth(): Promise<{ ok: boolean; error?: string | null }> {
  const res = await fetch("/api/health");
  return readJson(res);
}

export async function searchPersons(q: string): Promise<PersonHit[]> {
  const res = await fetch(`/api/persons?q=${encodeURIComponent(q)}`);
  return readJson(res);
}

export async function seedGraph(personId: string): Promise<GraphPayload> {
  const res = await fetch(
    `/api/graph/seed?person_id=${encodeURIComponent(personId)}`,
  );
  return readJson(res);
}

export async function expandGraph(
  id: string,
  label: string,
): Promise<GraphPayload> {
  const params = new URLSearchParams({ id, label });
  const res = await fetch(`/api/graph/expand?${params}`);
  return readJson(res);
}

export type AgentAskResponse = {
  answer: string;
  graph: GraphPayload;
  tools_used: string[];
};

export async function askAgent(question: string): Promise<AgentAskResponse> {
  const res = await fetch("/api/agent/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
  return readJson(res);
}
