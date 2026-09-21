#!/usr/bin/env python3
"""샘플 사건 데이터로 통화·이체 교차 분석을 실행한다.

적재는 bank/call CSV만 사용한다 (meta 미사용).
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from police_graph import CaseAnalyzer, create_schema, load_case_csvs, open_db


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DB_PATH = ROOT / "case.kuzu"


def _account_of(conn, person_id: str) -> str:
    row = conn.execute(
        """
        MATCH (p:Person {id: $pid})-[:OwnsAccount]->(a:Account)
        RETURN a.account_id LIMIT 1
        """,
        {"pid": person_id},
    ).get_next()
    return row[0]


def main() -> None:
    if DB_PATH.exists():
        shutil.rmtree(DB_PATH) if DB_PATH.is_dir() else DB_PATH.unlink()

    _, conn = open_db(DB_PATH)
    create_schema(conn)
    stats = load_case_csvs(conn, DATA)
    print(f"스키마·CSV 적재 완료 → {DB_PATH} ({stats})")

    gk_acct = _account_of(conn, "이영희")
    analyzer = CaseAnalyzer(conn)
    report = {
        "top_call_partners_김철수": analyzer.top_call_partners("김철수"),
        "money_flows_이영희": analyzer.money_flows_from(gk_acct, max_hops=2),
        "cross_link_call_and_transfer": analyzer.cross_link_call_and_transfer()[:10],
        "activity_hubs": analyzer.activity_hubs(),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
