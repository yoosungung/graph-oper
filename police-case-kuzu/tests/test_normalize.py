"""실무 포맷 CSV → 그래프 엔티티 정규화 테스트."""

from pathlib import Path

import pandas as pd

from police_graph.formats import BANK_COLUMNS, CALL_COLUMNS
from police_graph.normalize import normalize_bank_rows, normalize_call_rows


def _mini_bank_csv(path: Path) -> Path:
    rows = [
        {
            "입출금구분": "출금",
            "계좌주": "김철수",
            "금융기관": "국민은행",
            "계좌번호": "110-111-0001",
            "거래일자": "2024-06-02",
            "거래시간": "22:00:00",
            "거래종류": "이체",
            "취급점": "강남지점",
            "임금적요": "",
            "입금액": "0",
            "출금적요": "빌려준돈",
            "출금액": "5000000",
            "거래후잔액": "1000000",
            "상대은행": "신한은행",
            "상대예금주": "이영희",
            "상대계좌번호": "220-222-0002",
            "단말번호": "T001",
            "IP주소": "1.1.1.1",
            "MAC주소": "AA:BB:CC:DD:EE:01",
            "비고1": "",
            "비고2": "",
        },
        {
            "입출금구분": "입금",
            "계좌주": "이영희",
            "금융기관": "신한은행",
            "계좌번호": "220-222-0002",
            "거래일자": "2024-06-02",
            "거래시간": "22:01:00",
            "거래종류": "이체",
            "취급점": "역삼지점",
            "임금적요": "입금",
            "입금액": "5000000",
            "출금적요": "",
            "출금액": "0",
            "거래후잔액": "6000000",
            "상대은행": "국민은행",
            "상대예금주": "김철수",
            "상대계좌번호": "110-111-0001",
            "단말번호": "T002",
            "IP주소": "2.2.2.2",
            "MAC주소": "AA:BB:CC:DD:EE:02",
            "비고1": "",
            "비고2": "",
        },
    ]
    df = pd.DataFrame(rows, columns=BANK_COLUMNS)
    out = path / "bank_transactions.csv"
    df.to_csv(out, index=False)
    return out


def _mini_call_csv(path: Path) -> Path:
    rows = [
        {
            "발신인": "김철수",
            "발신번호": "010-1111-0001",
            "착신인": "이영희",
            "착신번호": "010-2222-0002",
            "시작일자": "2024-06-01",
            "시작시간": "10:00:00",
            "종료일자": "2024-06-01",
            "종료시간": "10:05:20",
            "통화시간(분)": "5.33",
            "업체명": "SKT",
            "발신위치": "서울 강남",
            "발신종료": "서울 강남",
            "비고1": "",
            "비고2": "",
        },
        {
            "발신인": "김철수",
            "발신번호": "010-1111-0001",
            "착신인": "이영희",
            "착신번호": "010-2222-0002",
            "시작일자": "2024-06-02",
            "시작시간": "21:15:00",
            "종료일자": "2024-06-02",
            "종료시간": "21:24:00",
            "통화시간(분)": "9",
            "업체명": "SKT",
            "발신위치": "서울 서초",
            "발신종료": "서울 서초",
            "비고1": "",
            "비고2": "",
        },
    ]
    df = pd.DataFrame(rows, columns=CALL_COLUMNS)
    out = path / "call_records.csv"
    df.to_csv(out, index=False)
    return out


def test_normalize_bank_builds_accounts_and_transfer(tmp_path: Path) -> None:
    csv_path = _mini_bank_csv(tmp_path)
    graph = normalize_bank_rows(pd.read_csv(csv_path, dtype=str).fillna(""))

    account_ids = {a["account_id"] for a in graph["accounts"]}
    assert "110-111-0001" in account_ids
    assert "220-222-0002" in account_ids

    person_ids = {p["id"] for p in graph["persons"]}
    assert "김철수" in person_ids
    assert "이영희" in person_ids

    # 출금 1건 → 김철수 계좌 → 이영희 계좌
    transfers = graph["transfers"]
    assert any(
        t["from_account"] == "110-111-0001"
        and t["to_account"] == "220-222-0002"
        and t["amount"] == 5_000_000.0
        for t in transfers
    )


def test_normalize_call_builds_phones_and_calls(tmp_path: Path) -> None:
    csv_path = _mini_call_csv(tmp_path)
    graph = normalize_call_rows(pd.read_csv(csv_path, dtype=str).fillna(""))

    phones = {p["number"] for p in graph["phones"]}
    assert "010-1111-0001" in phones
    assert "010-2222-0002" in phones

    assert len(graph["calls"]) == 2
    assert graph["calls"][0]["duration_sec"] == 320  # 5.33분 ≈ 320초
    assert graph["calls"][1]["duration_sec"] == 540
