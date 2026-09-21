"""Kuzu DB 연결 헬퍼."""

from __future__ import annotations

from pathlib import Path

import kuzu


def open_db(path: str | Path | None = None) -> tuple[kuzu.Database, kuzu.Connection]:
    """경로가 없으면 인메모리 DB를 연다."""
    db_path = ":memory:" if path is None else str(path)
    db = kuzu.Database(db_path)
    conn = kuzu.Connection(db)
    return db, conn
