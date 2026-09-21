import type cytoscape from "cytoscape";

export const graphStylesheet: cytoscape.StylesheetStyle[] = [
  {
    selector: "node",
    style: {
      label: "data(display)",
      "font-size": 11,
      "font-family": "IBM Plex Sans KR, Pretendard, sans-serif",
      color: "#1a2332",
      "text-valign": "bottom",
      "text-halign": "center",
      "text-margin-y": 6,
      "background-color": "#8aa0b4",
      width: 28,
      height: 28,
      "border-width": 2,
      "border-color": "#ffffff",
    },
  },
  {
    selector: 'node[label = "Person"]',
    style: {
      shape: "ellipse",
      "background-color": "#1f6f8b",
      width: 36,
      height: 36,
      color: "#0f2a36",
      "font-weight": 600,
    },
  },
  {
    selector: 'node[label = "Phone"]',
    style: {
      shape: "round-rectangle",
      "background-color": "#3d7a5a",
      width: 30,
      height: 22,
    },
  },
  {
    selector: 'node[label = "Account"]',
    style: {
      shape: "diamond",
      "background-color": "#c45c26",
      width: 30,
      height: 30,
    },
  },
  {
    selector: "node:selected",
    style: {
      "border-color": "#1a2332",
      "border-width": 3,
    },
  },
  {
    selector: "edge",
    style: {
      width: "data(width)",
      "line-color": "#8a9aab",
      "target-arrow-color": "#8a9aab",
      "target-arrow-shape": "triangle",
      "curve-style": "bezier",
      label: "data(display)",
      "font-size": 8,
      color: "#5a6b7d",
      "text-rotation": "autorotate",
      "text-margin-y": -8,
    },
  },
  {
    selector: 'edge[rel = "Called"]',
    style: {
      "line-color": "#3d7a5a",
      "target-arrow-color": "#3d7a5a",
    },
  },
  {
    selector: 'edge[rel = "Transferred"]',
    style: {
      "line-color": "#c45c26",
      "target-arrow-color": "#c45c26",
      "line-style": "solid",
    },
  },
  {
    selector: 'edge[rel = "OwnsPhone"], edge[rel = "OwnsAccount"]',
    style: {
      "line-color": "#1f6f8b",
      "target-arrow-color": "#1f6f8b",
      "line-style": "dashed",
      width: 1.2,
    },
  },
];
