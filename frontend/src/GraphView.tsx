import { useEffect, useRef } from "react";
import cytoscape, { type Core, type ElementDefinition } from "cytoscape";
import fcose from "cytoscape-fcose";
import type { GraphEdge, GraphPayload } from "./api";
import { edgeWidth } from "./edgeWidth";
import { formatDurationMin } from "./durationLabel";
import { formatAmountMan } from "./amountLabel";
import { expandGraph } from "./api";
import { expandLayout, relaxLayout, seedLayout } from "./fcoseOptions";
import { movedEnough, pullDelta, type Point } from "./dragNeighbors";
import { graphStylesheet } from "./styles";

cytoscape.use(fcose);

function edgeDisplay(edge: GraphEdge): string {
  if (edge.rel === "Called") {
    return `${edge.props.count}회 · ${formatDurationMin(edge.props.duration_sec)}`;
  }
  if (edge.rel === "Transferred") {
    return `${edge.props.count}회 · ${formatAmountMan(edge.props.amount)}`;
  }
  return edge.rel;
}

function toElements(payload: GraphPayload): ElementDefinition[] {
  const nodes: ElementDefinition[] = payload.nodes.map((n) => ({
    group: "nodes",
    data: {
      id: n.id,
      label: n.label,
      display: n.display,
      props: n.props,
      pk: String(
        n.props.id ?? n.props.number ?? n.props.account_id ?? n.display,
      ),
    },
  }));
  const edges: ElementDefinition[] = payload.edges.map((e) => ({
    group: "edges",
    data: {
      id: e.id,
      source: e.source,
      target: e.target,
      rel: e.rel,
      display: edgeDisplay(e),
      width: edgeWidth(e.rel, e.props),
      props: e.props,
    },
  }));
  return [...nodes, ...edges];
}

function mergeElements(cy: Core, payload: GraphPayload): number {
  const elements = toElements(payload);
  const fresh = elements.filter((el) => {
    const id = el.data?.id;
    return typeof id === "string" && cy.getElementById(id).empty();
  });
  if (fresh.length === 0) return 0;
  cy.add(fresh);
  return fresh.length;
}

type Props = {
  seed: GraphPayload | null;
  onSelect: (data: Record<string, unknown> | null) => void;
  onStatus: (message: string | null, isError?: boolean) => void;
  onExpanding: (busy: boolean) => void;
};

export default function GraphView({
  seed,
  onSelect,
  onStatus,
  onExpanding,
}: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const cyRef = useRef<Core | null>(null);
  const expandingRef = useRef(false);
  const dragRef = useRef<{ grab: Point; last: Point } | null>(null);

  useEffect(() => {
    if (!containerRef.current || cyRef.current) return;
    const cy = cytoscape({
      container: containerRef.current,
      style: graphStylesheet,
      layout: { name: "preset" },
      wheelSensitivity: 0.3,
      minZoom: 0.2,
      maxZoom: 3,
    });
    cyRef.current = cy;

    cy.on("tap", "node", (evt) => {
      const data = evt.target.data() as Record<string, unknown>;
      onSelect(data);
    });
    cy.on("tap", (evt) => {
      if (evt.target === cy) onSelect(null);
    });

    cy.on("grabon", "node", (evt) => {
      const p = evt.target.position();
      dragRef.current = { grab: { x: p.x, y: p.y }, last: { x: p.x, y: p.y } };
    });
    cy.on("drag", "node", (evt) => {
      const state = dragRef.current;
      if (!state) return;
      const p = evt.target.position();
      const delta = pullDelta(state.last, p);
      state.last = { x: p.x, y: p.y };
      evt.target
        .neighborhood()
        .nodes()
        .forEach((n: cytoscape.NodeSingular) => {
          if (n.locked()) return;
          const np = n.position();
          n.position({ x: np.x + delta.x, y: np.y + delta.y });
        });
    });
    cy.on("dragfreeon", "node", (evt) => {
      const state = dragRef.current;
      dragRef.current = null;
      if (!state || expandingRef.current) return;
      const node = evt.target;
      const p = node.position();
      if (!movedEnough(state.grab, p)) return;
      if (cy.nodes().length < 2) return;
      cy.layout(
        relaxLayout(node.id(), { x: p.x, y: p.y }) as cytoscape.LayoutOptions,
      ).run();
    });

    cy.on("dbltap", "node", async (evt) => {
      if (expandingRef.current) return;
      const node = evt.target;
      const pk = String(node.data("pk") ?? "");
      const label = String(node.data("label") ?? "");
      if (!pk || !label) return;

      expandingRef.current = true;
      onExpanding(true);
      onStatus(`확장 중: ${label}:${pk}`);
      try {
        const payload = await expandGraph(pk, label);
        const added = mergeElements(cy, payload);
        if (added > 0) {
          cy.layout(expandLayout() as cytoscape.LayoutOptions).run();
          onStatus(`+${added} elements`);
        } else {
          onStatus("이미 확장된 이웃입니다");
        }
      } catch (err) {
        onStatus(err instanceof Error ? err.message : "expand 실패", true);
      } finally {
        expandingRef.current = false;
        onExpanding(false);
      }
    });

    return () => {
      cy.destroy();
      cyRef.current = null;
    };
  }, [onExpanding, onSelect, onStatus]);

  useEffect(() => {
    const cy = cyRef.current;
    if (!cy || !seed) return;
    cy.elements().remove();
    cy.add(toElements(seed));
    cy.layout(seedLayout() as cytoscape.LayoutOptions).run();
    onSelect(null);
  }, [seed, onSelect]);

  return <div className="graph-canvas" ref={containerRef} />;
}
