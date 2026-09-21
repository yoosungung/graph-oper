"""Kuzu connection lifespan helpers."""

from __future__ import annotations

from pathlib import Path

import kuzu


def open_db(path: Path) -> tuple[kuzu.Database, kuzu.Connection]:
    if not path.exists():
        raise FileNotFoundError(f"Kuzu DB not found: {path}")
    db = kuzu.Database(str(path))
    conn = kuzu.Connection(db)
    return db, conn
