from __future__ import annotations

from pathlib import Path

from src.db import apply_schema, connect



def ensure_schema(db_path: Path, schema_sql_path: Path) -> None:
    """Initialize database schema if required tables do not exist.

    Args:
        db_path: Path to SQLite database.
        schema_sql_path: Path to SQL schema file.

    Returns:
        None.
    """
    conn = connect(db_path)
    try:
        apply_schema(conn, schema_sql_path)
    finally:
        conn.close()
