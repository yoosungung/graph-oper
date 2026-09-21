"""사건 그래프 스키마: 인물·전화·계좌 + 통화/이체 관계."""

from __future__ import annotations

import kuzu

DDL = [
    """
    CREATE NODE TABLE IF NOT EXISTS Person(
        id STRING PRIMARY KEY,
        name STRING,
        role STRING
    )
    """,
    """
    CREATE NODE TABLE IF NOT EXISTS Phone(
        number STRING PRIMARY KEY,
        carrier STRING
    )
    """,
    """
    CREATE NODE TABLE IF NOT EXISTS Account(
        account_id STRING PRIMARY KEY,
        bank STRING,
        account_type STRING
    )
    """,
    """
    CREATE REL TABLE IF NOT EXISTS OwnsPhone(
        FROM Person TO Phone,
        since STRING
    )
    """,
    """
    CREATE REL TABLE IF NOT EXISTS OwnsAccount(
        FROM Person TO Account
    )
    """,
    """
    CREATE REL TABLE IF NOT EXISTS Called(
        FROM Phone TO Phone,
        call_id STRING,
        started_at STRING,
        ended_at STRING,
        duration_sec INT64,
        call_type STRING,
        company STRING,
        location STRING,
        end_location STRING,
        note1 STRING,
        note2 STRING
    )
    """,
    """
    CREATE REL TABLE IF NOT EXISTS Transferred(
        FROM Account TO Account,
        tx_id STRING,
        amount DOUBLE,
        transferred_at STRING,
        memo STRING,
        direction STRING,
        tx_type STRING,
        branch STRING,
        balance_after DOUBLE,
        terminal STRING,
        ip STRING,
        mac STRING,
        note1 STRING,
        note2 STRING
    )
    """,
]


def create_schema(conn: kuzu.Connection) -> None:
    for statement in DDL:
        conn.execute(statement)
