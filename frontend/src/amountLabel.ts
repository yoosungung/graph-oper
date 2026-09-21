/** 합산 거래금액(원)을 라벨용 만원 문자열로 바꾼다. 소수 한 자리, 끝의 .0은 생략. */
export function formatAmountMan(won: unknown): string {
  const amount = Number(won);
  if (!Number.isFinite(amount)) return "?만원";
  const man = Math.round((amount / 10_000) * 10) / 10;
  const text = Number.isInteger(man)
    ? man.toLocaleString("ko-KR")
    : man.toLocaleString("ko-KR", {
        minimumFractionDigits: 1,
        maximumFractionDigits: 1,
      });
  return `${text}만원`;
}
