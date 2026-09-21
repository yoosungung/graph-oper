"""실무 CSV → 정규화 → Kuzu COPY 로더."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

import kuzu
import pandas as pd

from .formats import BANK_FILENAME, CALL_FILENAME
from .normalize import merge_graph_parts, normalize_bank_rows, normalize_call_rows


def _write_staging(graph: dict[str, list[dict[str, Any]]], staging: Path) -> None:
    staging.mkdir(parents=True, exist_ok=True)

    pd.DataFrame(graph["persons"]).to_csv(
        staging / "persons.csv", index=False, columns=["id", "name", "role"]
    )
    pd.DataFrame(graph["phones"]).to_csv(
        staging / "phones.csv", index=False, columns=["number", "carrier"]
    )
    pd.DataFrame(graph["accounts"]).to_csv(
        staging / "accounts.csv",
        index=False,
        columns=["account_id", "bank", "account_type"],
    )
    owns_phone = graph["owns_phone"]
    pd.DataFrame(owns_phone).to_csv(
        staging / "owns_phone.csv",
        index=False,
        columns=["from", "to", "since"],
    )
    pd.DataFrame(graph["owns_account"]).to_csv(
        staging / "owns_account.csv", index=False, columns=["from", "to"]
    )

    calls = [
        {
            "from": c["from_phone"],
            "to": c["to_phone"],
            "call_id": c["call_id"],
            "started_at": c["started_at"],
            "ended_at": c.get("ended_at", ""),
            "duration_sec": c["duration_sec"],
            "call_type": c.get("call_type", "voice"),
            "company": c.get("company", ""),
            "location": c.get("location", ""),
            "end_location": c.get("end_location", ""),
            "note1": c.get("note1", ""),
            "note2": c.get("note2", ""),
        }
        for c in graph["calls"]
    ]
    pd.DataFrame(calls).to_csv(staging / "calls.csv", index=False)

    transfers = [
        {
            "from": t["from_account"],
            "to": t["to_account"],
            "tx_id": t["tx_id"],
            "amount": t["amount"],
            "transferred_at": t["transferred_at"],
            "memo": t.get("memo", ""),
            "direction": t.get("direction", ""),
            "tx_type": t.get("tx_type", ""),
            "branch": t.get("branch", ""),
            "balance_after": t.get("balance_after", 0.0),
            "terminal": t.get("terminal", ""),
            "ip": t.get("ip", ""),
            "mac": t.get("mac", ""),
            "note1": t.get("note1", ""),
            "note2": t.get("note2", ""),
        }
        for t in graph["transfers"]
    ]
    pd.DataFrame(transfers).to_csv(staging / "transfers.csv", index=False)


def _copy_all(conn: kuzu.Connection, staging: Path) -> None:
    plan = [
        ("persons.csv", "Person"),
        ("phones.csv", "Phone"),
        ("accounts.csv", "Account"),
        ("owns_phone.csv", "OwnsPhone"),
        ("owns_account.csv", "OwnsAccount"),
        ("calls.csv", "Called"),
        ("transfers.csv", "Transferred"),
    ]
    for filename, table in plan:
        path = (staging / filename).resolve()
        if not path.exists() or path.stat().st_size == 0:
            # 헤더만 있는 빈 테이블은 스킵
            continue
        # 데이터 행이 있는지 확인
        with path.open(encoding="utf-8") as f:
            lines = sum(1 for _ in f)
        if lines <= 1:
            continue
        conn.execute(f'COPY {table} FROM "{path}" (header=true)')


def load_case_csvs(
    conn: kuzu.Connection,
    data_dir: str | Path,
    *,
    bank_file: str = BANK_FILENAME,
    call_file: str = CALL_FILENAME,
) -> dict[str, int]:
    """실무 포맷 `bank_transactions.csv` + `call_records.csv`를 적재한다."""
    root = Path(data_dir)
    bank_path = root / bank_file
    call_path = root / call_file
    if not bank_path.exists():
        raise FileNotFoundError(f"필수 CSV 없음: {bank_path}")
    if not call_path.exists():
        raise FileNotFoundError(f"필수 CSV 없음: {call_path}")

    bank_df = pd.read_csv(bank_path, dtype=str).fillna("")
    call_df = pd.read_csv(call_path, dtype=str).fillna("")
    graph = merge_graph_parts(
        normalize_bank_rows(bank_df),
        normalize_call_rows(call_df),
    )

    with tempfile.TemporaryDirectory(prefix="police_graph_") as tmp:
        staging = Path(tmp)
        _write_staging(graph, staging)
        _copy_all(conn, staging)

    return {
        "persons": len(graph["persons"]),
        "phones": len(graph["phones"]),
        "accounts": len(graph["accounts"]),
        "calls": len(graph["calls"]),
        "transfers": len(graph["transfers"]),
    }
