"""통화·이체 교차 분석 쿼리."""

from __future__ import annotations

from typing import Any

import kuzu


def _rows(result: Any) -> list[list[Any]]:
    out: list[list[Any]] = []
    while result.has_next():
        out.append(result.get_next())
    return out


def _num(value: Any) -> Any:
    """Kuzu INT64/DOUBLE/Decimal을 JSON 친화 타입으로 변환."""
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return int(value)
    if isinstance(value, float):
        return float(value)
    # decimal.Decimal 등
    try:
        from decimal import Decimal

        if isinstance(value, Decimal):
            return float(value)
    except Exception:
        pass
    return value


def _row_dict(keys: list[str], row: list[Any]) -> dict[str, Any]:
    return {k: _num(v) if not isinstance(v, str) else v for k, v in zip(keys, row)}


class CaseAnalyzer:
    def __init__(self, conn: kuzu.Connection) -> None:
        self.conn = conn

    def top_call_partners(
        self, person_id: str, limit: int = 5
    ) -> list[dict[str, Any]]:
        """특정 인물과 가장 많이 통화한 상대."""
        result = self.conn.execute(
            """
            MATCH (p:Person {id: $pid})-[:OwnsPhone]->(ph:Phone)
                  -[c:Called]-(other_ph:Phone)<-[:OwnsPhone]-(other:Person)
            WHERE other.id <> $pid
            RETURN other.id AS person_id,
                   other.name AS name,
                   count(c) AS call_count,
                   sum(c.duration_sec) AS total_duration_sec
            ORDER BY call_count DESC
            LIMIT $lim
            """,
            {"pid": person_id, "lim": limit},
        )
        return [
            _row_dict(
                ["person_id", "name", "call_count", "total_duration_sec"], r
            )
            for r in _rows(result)
        ]

    def money_flows_from(
        self, account_id: str, max_hops: int = 2
    ) -> list[dict[str, Any]]:
        """출발 계좌에서 직접(1홉) 및 경유(2홉) 자금 흐름 집계."""
        result = self.conn.execute(
            """
            MATCH (src:Account {account_id: $aid})-[t:Transferred]->(dst:Account)
            RETURN dst.account_id AS to_account,
                   sum(t.amount) AS total_amount,
                   count(t) AS hop_edges,
                   1 AS hops
            ORDER BY total_amount DESC
            """,
            {"aid": account_id},
        )
        flows = [
            _row_dict(["to_account", "total_amount", "hop_edges", "hops"], r)
            for r in _rows(result)
        ]
        if max_hops >= 2:
            result2 = self.conn.execute(
                """
                MATCH (src:Account {account_id: $aid})
                      -[t1:Transferred]->(mid:Account)
                      -[t2:Transferred]->(dst:Account)
                WHERE dst.account_id <> src.account_id
                RETURN dst.account_id AS to_account,
                       sum(t1.amount + t2.amount) AS total_amount,
                       count(*) AS hop_edges,
                       2 AS hops
                ORDER BY total_amount DESC
                """,
                {"aid": account_id},
            )
            flows.extend(
                _row_dict(["to_account", "total_amount", "hop_edges", "hops"], r)
                for r in _rows(result2)
            )
        return flows

    def cross_link_call_and_transfer(self) -> list[dict[str, Any]]:
        """통화와 이체가 모두 있는 인물 쌍 (공범 후보)."""
        result = self.conn.execute(
            """
            MATCH (a:Person)-[:OwnsPhone]->(aph:Phone)
                  -[c:Called]-(bph:Phone)<-[:OwnsPhone]-(b:Person)
            WHERE a.id < b.id
            WITH DISTINCT a, b
            MATCH (a)-[:OwnsAccount]->(aa:Account)
                  -[t:Transferred]-(ba:Account)<-[:OwnsAccount]-(b)
            RETURN a.id AS person_a,
                   a.name AS name_a,
                   b.id AS person_b,
                   b.name AS name_b,
                   count(t) AS transfer_count
            ORDER BY transfer_count DESC
            """
        )
        return [
            _row_dict(
                ["person_a", "name_a", "person_b", "name_b", "transfer_count"],
                r,
            )
            for r in _rows(result)
        ]

    def activity_hubs(self, limit: int = 5) -> list[dict[str, Any]]:
        """통화(가중 2) + 이체(가중 1)로 활동 허브 점수."""
        result = self.conn.execute(
            """
            MATCH (p:Person)
            OPTIONAL MATCH (p)-[:OwnsPhone]->(:Phone)-[c:Called]-()
            OPTIONAL MATCH (p)-[:OwnsAccount]->(:Account)-[t:Transferred]-()
            RETURN p.id AS person_id,
                   p.name AS name,
                   count(DISTINCT c) * 2 + count(DISTINCT t) AS score
            ORDER BY score DESC
            LIMIT $lim
            """,
            {"lim": limit},
        )
        return [
            _row_dict(["person_id", "name", "score"], r) for r in _rows(result)
        ]
