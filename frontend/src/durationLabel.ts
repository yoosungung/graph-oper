/** 합산 통화시간(초)을 라벨용 분 문자열로 바꾼다. 소수 한 자리, 끝의 .0은 생략. */
export function formatDurationMin(seconds: unknown): string {
  const sec = Number(seconds);
  if (!Number.isFinite(sec)) return "?분";
  const rounded = Math.round((sec / 60) * 10) / 10;
  const text = Number.isInteger(rounded) ? String(rounded) : rounded.toFixed(1);
  return `${text}분`;
}
