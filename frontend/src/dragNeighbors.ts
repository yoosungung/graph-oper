export const NEIGHBOR_PULL = 0.55;
export const RELAX_MIN_PX = 8;

export type Point = { x: number; y: number };

export function pullDelta(from: Point, to: Point, pull = NEIGHBOR_PULL): Point {
  return { x: (to.x - from.x) * pull, y: (to.y - from.y) * pull };
}

export function movedEnough(from: Point, to: Point, min = RELAX_MIN_PX): boolean {
  const dx = to.x - from.x;
  const dy = to.y - from.y;
  return dx * dx + dy * dy >= min * min;
}
