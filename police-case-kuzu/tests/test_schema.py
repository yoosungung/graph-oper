"""스키마 생성 테스트 (TDD Step 1)."""

from pathlib import Path

import kuzu

from police_graph.schema import create_schema


def test_create_schema_defines_node_and_rel_tables(tmp_path: Path) -> None:
    db = kuzu.Database(str(tmp_path / "schema.kuzu"))
    conn = kuzu.Connection(db)

    create_schema(conn)

    # show_tables(): id, name, type, database name, comment
    tables = {
        row[1]
        for row in conn.execute("CALL show_tables() RETURN *")
    }
    assert "Person" in tables
    assert "Phone" in tables
    assert "Account" in tables
    assert "OwnsPhone" in tables
    assert "OwnsAccount" in tables
    assert "Called" in tables
    assert "Transferred" in tables
