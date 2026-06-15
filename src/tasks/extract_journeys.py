from __future__ import annotations

import sqlite3

import pandas as pd



def build_customer_journeys(
    conn: sqlite3.Connection,
    start_date: str | None = None,
    end_date: str | None = None,
    max_conversions: int | None = None,
) -> pd.DataFrame:
    """Build conversion journeys by joining conversions to prior user sessions.

    Args:
        conn: Active SQLite connection.
        start_date: Optional inclusive conversion-date lower bound.
        end_date: Optional inclusive conversion-date upper bound.
        max_conversions: Optional maximum number of conversion journeys.

    Returns:
        DataFrame of session-level journey rows ordered by conversion and time.
    """
    where_clauses: list[str] = []
    params: list[str] = []

    if start_date:
        where_clauses.append("c.conv_date >= ?")
        params.append(start_date)

    if end_date:
        where_clauses.append("c.conv_date <= ?")
        params.append(end_date)

    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

    query = f"""
        WITH selected_conversions AS (
            SELECT
                c.conv_id,
                c.user_id,
                c.conv_date,
                c.conv_time,
                c.revenue
            FROM conversions c
            {where_sql}
            ORDER BY datetime(c.conv_date || ' ' || c.conv_time)
            {"LIMIT ?" if max_conversions is not None and max_conversions > 0 else ""}
        )
        SELECT
            c.conv_id,
            c.user_id,
            c.conv_date,
            c.conv_time,
            c.revenue,
            s.session_id,
            s.event_date,
            s.event_time,
            s.channel_name,
            s.holder_engagement,
            s.closer_engagement,
            s.impression_interaction
        FROM selected_conversions c
        INNER JOIN session_sources s
            ON c.user_id = s.user_id
           AND datetime(s.event_date || ' ' || s.event_time) < datetime(c.conv_date || ' ' || c.conv_time)
        ORDER BY c.conv_id, datetime(s.event_date || ' ' || s.event_time)
    """

    if max_conversions is not None and max_conversions > 0:
        params.append(str(max_conversions))

    return pd.read_sql_query(query, conn, params=params)



def journeys_to_api_payload(
    journeys_df: pd.DataFrame, max_journeys: int | None = None
) -> list[dict]:
    """Convert journey dataframe into IHC `customer_journeys` payload format.

    Args:
        journeys_df: DataFrame from `build_customer_journeys`.
        max_journeys: Optional cap on number of unique conversions included.

    Returns:
        Flat list of session-level dictionaries ready for IHC API submission.
    """
    if journeys_df.empty:
        return []

    payload: list[dict] = []

    journey_count = 0
    for conv_id, group in journeys_df.groupby("conv_id", sort=False):
        if max_journeys is not None and max_journeys > 0 and journey_count >= max_journeys:
            break

        ordered = group.sort_values(by=["event_date", "event_time"], kind="stable")
        last_idx = len(ordered) - 1

        for idx, (_, row) in enumerate(ordered.iterrows()):
            payload.append(
                {
                    "conversion_id": str(conv_id),
                    "session_id": str(row["session_id"]),
                    "timestamp": f"{row['event_date']} {row['event_time']}",
                    "channel_label": str(row["channel_name"]),
                    "holder_engagement": int(row["holder_engagement"]),
                    "closer_engagement": int(row["closer_engagement"]),
                    "conversion": 1 if idx == last_idx else 0,
                    "impression_interaction": int(row["impression_interaction"]),
                }
            )

        journey_count += 1

    return payload
