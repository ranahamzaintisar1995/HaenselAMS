from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

from src.tasks.extract_journeys import build_customer_journeys, journeys_to_api_payload


def export_customer_journeys_csv(
    conn: sqlite3.Connection,
    output_path: Path,
    start_date: str | None = None,
    end_date: str | None = None,
    max_journeys: int | None = None,
) -> tuple[Path, int, int]:
    """Export transformed IHC customer journeys into upload-ready CSV.

    Args:
        conn: Active SQLite connection.
        output_path: Target CSV path.
        start_date: Optional conversion-date lower bound.
        end_date: Optional conversion-date upper bound.
        max_journeys: Optional cap on number of unique conversion journeys.

    Returns:
        Tuple of `(output_path, journey_count, session_row_count)`.
    """
    journeys_df = build_customer_journeys(
        conn,
        start_date=start_date,
        end_date=end_date,
        max_conversions=max_journeys,
    )

    payload = journeys_to_api_payload(journeys_df, max_journeys=max_journeys)
    payload_df = pd.DataFrame(payload)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload_df.to_csv(output_path, index=False)

    unique_journeys = len(
        {
            str(item.get("conversion_id", ""))
            for item in payload
            if item.get("conversion_id")
        }
    )

    return output_path, unique_journeys, len(payload)