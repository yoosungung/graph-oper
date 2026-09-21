#!/usr/bin/env python3
"""data/ 샘플 CSV → sample.db 적재."""

from __future__ import annotations

import shutil
from pathlib import Path

from police_graph import create_schema, load_case_csvs, open_db

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DB_PATH = ROOT / "sample.db"


def main() -> None:
    if DB_PATH.exists():
        shutil.rmtree(DB_PATH) if DB_PATH.is_dir() else DB_PATH.unlink()

    _, conn = open_db(DB_PATH)
    create_schema(conn)
    stats = load_case_csvs(conn, DATA)
    print(f"스키마·CSV 적재 완료 → {DB_PATH}")
    print(f"stats: {stats}")
    for label, q in [
        ("Person", "MATCH (p:Person) RETURN count(p)"),
        ("Phone", "MATCH (ph:Phone) RETURN count(ph)"),
        ("Account", "MATCH (a:Account) RETURN count(a)"),
        ("Called", "MATCH ()-[c:Called]->() RETURN count(c)"),
        ("Transferred", "MATCH ()-[t:Transferred]->() RETURN count(t)"),
    ]:
        print(f"  {label}: {conn.execute(q).get_next()[0]}")


if __name__ == "__main__":
    main()
