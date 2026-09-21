"""CSV 로더 테스트."""

from pathlib import Path

import kuzu

from police_graph.loader import load_case_csvs
from police_graph.sample_gen import generate_sample_data
from police_graph.schema import create_schema


def test_load_case_csvs_from_raw_format(tmp_path: Path) -> None:
    generate_sample_data(tmp_path, n_bank=50, n_call=50, seed=1)
    db = kuzu.Database(str(tmp_path / "load.kuzu"))
    conn = kuzu.Connection(db)
    create_schema(conn)

    stats = load_case_csvs(conn, tmp_path)

    person_count = conn.execute("MATCH (p:Person) RETURN count(p)").get_next()[0]
    phone_count = conn.execute("MATCH (ph:Phone) RETURN count(ph)").get_next()[0]
    account_count = conn.execute("MATCH (a:Account) RETURN count(a)").get_next()[0]
    call_count = conn.execute("MATCH ()-[c:Called]->() RETURN count(c)").get_next()[0]
    tx_count = conn.execute(
        "MATCH ()-[t:Transferred]->() RETURN count(t)"
    ).get_next()[0]

    assert stats["calls"] == 50
    assert stats["transfers"] == 50
    assert person_count >= 4
    assert phone_count >= 4
    assert account_count >= 4
    assert call_count == 50
    assert tx_count == 50
