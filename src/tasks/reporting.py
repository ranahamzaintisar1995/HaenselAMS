from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

from src.db import replace_channel_reporting



def build_channel_reporting(conn: sqlite3.Connection) -> int:
    """Build and persist channel/date reporting aggregates.

    Args:
        conn: Active SQLite connection.

    Returns:
        Number of reporting rows written to `channel_reporting`.
    """
    query = """
        WITH session_base AS (
            SELECT
                s.session_id,
                s.channel_name,
                s.event_date AS date,
                COALESCE(sc.cost, 0.0) AS cost
            FROM session_sources s
            LEFT JOIN session_costs sc ON s.session_id = sc.session_id
        ),
        costs AS (
            SELECT
                channel_name,
                date,
                SUM(cost) AS cost
            FROM session_base
            GROUP BY channel_name, date
        ),
        attribution AS (
            SELECT
                s.channel_name,
                s.event_date AS date,
                SUM(acj.ihc) AS ihc,
                SUM(acj.ihc * c.revenue) AS ihc_revenue
            FROM attribution_customer_journey acj
            INNER JOIN session_sources s ON acj.session_id = s.session_id
            INNER JOIN conversions c ON acj.conv_id = c.conv_id
            GROUP BY s.channel_name, s.event_date
        )
        SELECT
            co.channel_name,
            co.date,
            co.cost,
            COALESCE(at.ihc, 0.0) AS ihc,
            COALESCE(at.ihc_revenue, 0.0) AS ihc_revenue
        FROM costs co
        LEFT JOIN attribution at
            ON co.channel_name = at.channel_name
           AND co.date = at.date
        ORDER BY co.date, co.channel_name
    """

    df = pd.read_sql_query(query, conn)
    rows = [tuple(x) for x in df.to_records(index=False)]
    return replace_channel_reporting(conn, rows)



def export_channel_reporting_csv(conn: sqlite3.Connection, output_path: Path) -> Path:
    """Export channel reporting data to CSV with derived KPI columns.

    Args:
        conn: Active SQLite connection.
        output_path: Target CSV path.

    Returns:
        Path to the written CSV file.
    """
    df = pd.read_sql_query(
        """
        SELECT channel_name, date, cost, ihc, ihc_revenue
        FROM channel_reporting
        ORDER BY date, channel_name
        """,
        conn,
    )

    if df.empty:
        df["CPO"] = pd.Series(dtype="float64")
        df["ROAS"] = pd.Series(dtype="float64")
    else:
        df["CPO"] = df.apply(
            lambda r: (r["cost"] / r["ihc"]) if r["ihc"] > 0 else float("nan"), axis=1
        )
        df["ROAS"] = df.apply(
            lambda r: (r["ihc_revenue"] / r["cost"]) if r["cost"] > 0 else float("nan"),
            axis=1,
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    return output_path
