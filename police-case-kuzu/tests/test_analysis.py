"""분석 쿼리 테스트 — 공범 후보·자금흐름."""

from pathlib import Path

import kuzu

from police_graph.analysis import CaseAnalyzer
from police_graph.loader import load_case_csvs
from police_graph.sample_gen import generate_sample_data
from police_graph.schema import create_schema


def _seeded_conn(tmp_path: Path) -> kuzu.Connection:
    # 조직 패턴이 충분히 들어가도록 건수 확보
    generate_sample_data(tmp_path, n_bank=400, n_call=400, seed=42)
    db = kuzu.Database(str(tmp_path / "analysis.kuzu"))
    conn = kuzu.Connection(db)
    create_schema(conn)
    load_case_csvs(conn, tmp_path)
    return conn


def test_top_call_partners_for_suspect(tmp_path: Path) -> None:
    analyzer = CaseAnalyzer(_seeded_conn(tmp_path))
    partners = analyzer.top_call_partners("김철수", limit=3)

    assert partners
    assert partners[0]["person_id"] == "이영희"
    assert partners[0]["call_count"] >= 2


def test_money_flow_from_account(tmp_path: Path) -> None:
    conn = _seeded_conn(tmp_path)
    analyzer = CaseAnalyzer(conn)

    def account_of(name: str) -> str:
        return conn.execute(
            """
            MATCH (p:Person {id: $pid})-[:OwnsAccount]->(a:Account)
            RETURN a.account_id LIMIT 1
            """,
            {"pid": name},
        ).get_next()[0]

    boss_acct = account_of("김철수")
    gk_acct = account_of("이영희")
    flows = analyzer.money_flows_from(gk_acct, max_hops=2)

    assert flows
    assert any(row["to_account"] == boss_acct for row in flows)
    assert any(row["total_amount"] >= 5_000_000 for row in flows)


def test_cross_link_call_and_transfer(tmp_path: Path) -> None:
    """통화와 이체가 모두 있는 인물 쌍 = 공범 후보."""
    analyzer = CaseAnalyzer(_seeded_conn(tmp_path))
    links = analyzer.cross_link_call_and_transfer()

    pair_ids = {(row["person_a"], row["person_b"]) for row in links}
    assert ("김철수", "이영희") in pair_ids or ("이영희", "김철수") in pair_ids


def test_hub_persons_by_activity(tmp_path: Path) -> None:
    analyzer = CaseAnalyzer(_seeded_conn(tmp_path))
    hubs = analyzer.activity_hubs(limit=5)
    hub_ids = {h["person_id"] for h in hubs}

    # gate-keeper / 영업-hub 가 활동 허브로 떠야 함
    assert hub_ids & {"이영희", "박민수", "최지훈", "정하늘", "김철수"}
    assert hubs[0]["score"] >= hubs[1]["score"]
