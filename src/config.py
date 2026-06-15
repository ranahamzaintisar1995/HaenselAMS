from __future__ import annotations

import os
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    project_root: Path
    db_path: Path
    schema_sql_path: Path
    output_csv_path: Path
    ihc_api_url: str
    ihc_api_key: str | None
    ihc_conv_type_id: str
    ihc_redistribution_parameter: dict[str, Any] | None
    ihc_max_journeys_per_run: int
    ihc_chunk_size: int
    ihc_max_sessions_per_request: int
    ihc_timeout_seconds: int



def load_settings(project_root: Path | None = None) -> Settings:
    """Load runtime settings from environment variables.

    The function reads variables from `.env` (if present), applies defaults,
    parses optional JSON configuration, and returns a strongly typed `Settings`
    object consumed by the pipeline.

    Args:
        project_root: Optional project root path. If omitted, the repository
            root inferred from this file location is used.

    Returns:
        A populated `Settings` instance with database paths, API configuration,
        batching limits, and timeout values.
    """
    root = project_root or Path(__file__).resolve().parents[1]
    load_dotenv(root / ".env")

    db_path = Path(os.getenv("ATTRIBUTION_DB_PATH", str(root / "challenge.db")))
    schema_sql_path = Path(
        os.getenv("ATTRIBUTION_SCHEMA_SQL_PATH", str(root / "challenge_db_create.sql"))
    )
    output_csv_path = Path(
        os.getenv("ATTRIBUTION_OUTPUT_CSV", str(root / "channel_reporting.csv"))
    )

    redistribution_parameter: dict[str, Any] | None = None
    raw_redistribution = os.getenv("IHC_REDISTRIBUTION_PARAMETER")
    if raw_redistribution:
        try:
            parsed = json.loads(raw_redistribution)
            if isinstance(parsed, dict):
                redistribution_parameter = parsed
        except json.JSONDecodeError:
            redistribution_parameter = None

    return Settings(
        project_root=root,
        db_path=db_path,
        schema_sql_path=schema_sql_path,
        output_csv_path=output_csv_path,
        ihc_api_url=os.getenv("IHC_API_URL", "https://api.ihc-attribution.com/v1/compute_ihc"),
        ihc_api_key=os.getenv("IHC_API_KEY"),
        ihc_conv_type_id=os.getenv("IHC_CONV_TYPE_ID", "default"),
        ihc_redistribution_parameter=redistribution_parameter,
        ihc_max_journeys_per_run=int(os.getenv("IHC_MAX_JOURNEYS_PER_RUN", "100")),
        ihc_chunk_size=int(os.getenv("IHC_CHUNK_SIZE", "200")),
        ihc_max_sessions_per_request=int(os.getenv("IHC_MAX_SESSIONS_PER_REQUEST", "200")),
        ihc_timeout_seconds=int(os.getenv("IHC_REQUEST_TIMEOUT_SECONDS", "30")),
    )
