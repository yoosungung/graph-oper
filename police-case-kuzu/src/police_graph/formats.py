"""실무 CSV 컬럼 상수 (은행거래 · 통화내역)."""

from __future__ import annotations

# 사용자 제공 원본 헤더 (임금적요 = 입금적요 표기)
BANK_COLUMNS = [
    "입출금구분",
    "계좌주",
    "금융기관",
    "계좌번호",
    "거래일자",
    "거래시간",
    "거래종류",
    "취급점",
    "임금적요",
    "입금액",
    "출금적요",
    "출금액",
    "거래후잔액",
    "상대은행",
    "상대예금주",
    "상대계좌번호",
    "단말번호",
    "IP주소",
    "MAC주소",
    "비고1",
    "비고2",
]

CALL_COLUMNS = [
    "발신인",
    "발신번호",
    "착신인",
    "착신번호",
    "시작일자",
    "시작시간",
    "종료일자",
    "종료시간",
    "통화시간(분)",
    "업체명",
    "발신위치",
    "발신종료",
    "비고1",
    "비고2",
]

BANK_FILENAME = "bank_transactions.csv"
CALL_FILENAME = "call_records.csv"

# 보조 메타데이터 (실무 입력 포맷이 아님) → data/meta/
META_DIRNAME = "meta"
ROSTER_FILENAME = "persons_roster.csv"
TIMELINE_FILENAME = "phone_timeline.csv"
