from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable


def _clean_sql_script(raw_sql: str) -> str:
    """Sanitize schema SQL text before execution.

    The challenge schema file may contain Python-style comments or triple-quoted
    header blocks. This helper removes those non-SQL lines so SQLite can execute
    the script safely.

    Args:
        raw_sql: Raw file content loaded from a schema `.sql` file.

    Returns:
        Cleaned SQL script string containing only executable SQL statements.
    """
    cleaned_lines: list[str] = []
    in_triple_quote_block = False

    for line in raw_sql.splitlines():
        stripped = line.strip()

        if stripped.startswith('"""'):
            in_triple_quote_block = not in_triple_quote_block
            continue

        if in_triple_quote_block:
            continue

        if stripped.startswith("#"):
            continue

        cleaned_lines.append(line)

    return "\n".join(cleaned_lines)


def connect(db_path: Path) -> sqlite3.Connection:
    """Create a SQLite connection configured for dict-like row access.

    Args:
        db_path: Path to the SQLite database file.

    Returns:
        Open `sqlite3.Connection` object with `sqlite3.Row` row factory.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn



def apply_schema(conn: sqlite3.Connection, schema_sql_path: Path) -> None:
    """Apply database schema statements from a SQL file.

    Args:
        conn: Active SQLite connection.
        schema_sql_path: Path to schema file containing CREATE TABLE statements.

    Returns:
        None.
    """
    schema_sql = _clean_sql_script(schema_sql_path.read_text(encoding="utf-8"))
    conn.executescript(schema_sql)
    conn.commit()



def upsert_attribution_rows(
    conn: sqlite3.Connection, rows: Iterable[tuple[str, str, float]]
) -> int:
    """Insert or update attribution rows in the customer journey table.

    Args:
        conn: Active SQLite connection.
        rows: Iterable of `(conv_id, session_id, ihc)` tuples.

    Returns:
        Number of rows processed.
    """
    payload = list(rows)
    if not payload:
        return 0

    conn.executemany(
        """
        INSERT INTO attribution_customer_journey (conv_id, session_id, ihc)
        VALUES (?, ?, ?)
        ON CONFLICT(conv_id, session_id)
        DO UPDATE SET ihc = excluded.ihc
        """,
        payload,
    )
    conn.commit()
    return len(payload)



def replace_channel_reporting(
    conn: sqlite3.Connection, rows: Iterable[tuple[str, str, float, float, float]]
) -> int:
    """Replace channel reporting table contents with new aggregate rows.

    Args:
        conn: Active SQLite connection.
        rows: Iterable of `(channel_name, date, cost, ihc, ihc_revenue)` tuples.

    Returns:
        Number of rows written.
    """
    payload = list(rows)
    conn.execute("DELETE FROM channel_reporting")

    if payload:
        conn.executemany(
            """
            INSERT INTO channel_reporting (channel_name, date, cost, ihc, ihc_revenue)
            VALUES (?, ?, ?, ?, ?)
            """,
            payload,
        )

    conn.commit()
    return len(payload)
