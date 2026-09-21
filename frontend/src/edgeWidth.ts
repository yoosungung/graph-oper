const MIN_WIDTH = 1.2;
const MAX_WIDTH = 8;

/** log10(횟수 × 량)을 1.2–8 두께로 맞춘다. 량은 통화시간 또는 거래금액. */
export function edgeWidth(
  rel: string,
  props: Record<string, unknown>,
): number {
  if (rel !== "Called" && rel !== "Transferred") return MIN_WIDTH;
  const count = Number(props.count);
  const qty = Number(rel === "Called" ? props.duration_sec : props.amount);
  if (!Number.isFinite(count) || count <= 0 || !Number.isFinite(qty) || qty <= 0) {
    return MIN_WIDTH;
  }
  const score = Math.log10(count * qty);
  const width = MIN_WIDTH + ((score - 1) / 7) * (MAX_WIDTH - MIN_WIDTH);
  const clamped = Math.min(MAX_WIDTH, Math.max(MIN_WIDTH, width));
  return Math.round(clamped * 10) / 10;
}
