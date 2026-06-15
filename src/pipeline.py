from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from src.config import Settings
from src.db import connect, upsert_attribution_rows
from src.ihc_client import IhcClient
from src.tasks.attribution import (
    normalize_attribution_rows,
    score_customer_journeys,
    validate_ihc_sums,
)
from src.tasks.extract_journeys import build_customer_journeys, journeys_to_api_payload
from src.tasks.reporting import build_channel_reporting, export_channel_reporting_csv
from src.tasks.setup import ensure_schema


@dataclass
class PipelineResult:
    journeys_count: int
    attribution_rows_count: int
    channel_reporting_rows_count: int
    csv_path: str
    ihc_sum_violations: list[tuple[str, float]]
    api_calls_made: int



def run_pipeline(
    settings: Settings,
    start_date: str | None = None,
    end_date: str | None = None,
    use_mock_api: bool = False,
) -> PipelineResult:
    """Run the complete attribution pipeline from extraction to reporting export.

    Args:
        settings: Runtime configuration including DB, API, and batching limits.
        start_date: Optional inclusive conversion-date lower bound (`YYYY-MM-DD`).
        end_date: Optional inclusive conversion-date upper bound (`YYYY-MM-DD`).
        use_mock_api: If true, bypass IHC API and compute deterministic local
            attribution values.

    Returns:
        `PipelineResult` containing processing counts, output path, and API call
        metrics.
    """
    ensure_schema(settings.db_path, settings.schema_sql_path)

    conn = connect(settings.db_path)
    try:
        max_journeys = (
            settings.ihc_max_journeys_per_run
            if settings.ihc_max_journeys_per_run > 0
            else None
        )

        journeys_df = build_customer_journeys(
            conn,
            start_date=start_date,
            end_date=end_date,
            max_conversions=max_journeys,
        )
        journey_payload = journeys_to_api_payload(
            journeys_df, max_journeys=max_journeys
        )

        client = IhcClient(
            api_url=settings.ihc_api_url,
            api_key=settings.ihc_api_key,
            conv_type_id=settings.ihc_conv_type_id,
            redistribution_parameter=settings.ihc_redistribution_parameter,
            timeout_seconds=settings.ihc_timeout_seconds,
        )

        attribution_rows = score_customer_journeys(
            journeys=journey_payload,
            client=client,
            chunk_size=settings.ihc_chunk_size,
            max_sessions_per_request=settings.ihc_max_sessions_per_request,
            use_mock=use_mock_api,
        )

        unique_journeys = len({
            str(item.get("conversion_id", ""))
            for item in journey_payload
            if item.get("conversion_id")
        })

        normalized_rows = normalize_attribution_rows(attribution_rows)
        written_count = upsert_attribution_rows(conn, normalized_rows)
        ihc_sum_violations = validate_ihc_sums(normalized_rows)

        channel_reporting_count = build_channel_reporting(conn)
        csv_path = export_channel_reporting_csv(conn, settings.output_csv_path)

        return PipelineResult(
            journeys_count=unique_journeys,
            attribution_rows_count=written_count,
            channel_reporting_rows_count=channel_reporting_count,
            csv_path=str(csv_path),
            ihc_sum_violations=ihc_sum_violations,
            api_calls_made=client.call_count,
        )
    finally:
        conn.close()
