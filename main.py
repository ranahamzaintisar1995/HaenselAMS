from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from src.config import load_settings
from src.db import connect
from src.pipeline import run_pipeline
from src.tasks.export_journeys_csv import export_customer_journeys_csv


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


def parse_args() -> argparse.Namespace:
    """Parse supported CLI arguments for all run modes.

    Returns:
        Parsed `argparse.Namespace` with pipeline filters, mock mode flag,
        and customer-journey CSV export options.
    """
    parser = argparse.ArgumentParser(description="Run attribution pipeline")
    parser.add_argument("--start-date", type=str, default=None, help="YYYY-MM-DD")
    parser.add_argument("--end-date", type=str, default=None, help="YYYY-MM-DD")
    parser.add_argument(
        "--mock-api",
        action="store_true",
        help="Use deterministic local attribution instead of the remote IHC API",
    )
    parser.add_argument(
        "--project-root",
        type=str,
        default=str(Path(__file__).resolve().parent),
        help="Project root for resolving DB and config paths",
    )
    parser.add_argument(
        "--export-journeys-csv",
        action="store_true",
        help="Export transformed IHC customer_journeys payload to CSV and exit",
    )
    parser.add_argument(
        "--journeys-csv-path",
        type=str,
        default="ihc_customer_journeys.csv",
        help="Output path for --export-journeys-csv mode",
    )
    return parser.parse_args()



def main() -> None:
    """Execute the selected command mode.

    The function loads settings, logs runtime configuration, then either:
    1. exports transformed customer journeys CSV and exits, or
    2. runs the full attribution pipeline.

    Returns:
        None.
    """
    args = parse_args()
    settings = load_settings(Path(args.project_root))
    
    logger = logging.getLogger(__name__)
    logger.info(f"Using API URL: {settings.ihc_api_url}")
    logger.info(f"Using conv_type_id: {settings.ihc_conv_type_id}")
    logger.info(f"Using API key: {settings.ihc_api_key[:20]}..." if settings.ihc_api_key else "No API key")
    logger.info(f"Max journeys per run: {settings.ihc_max_journeys_per_run}")
    logger.info(f"Chunk size: {settings.ihc_chunk_size}")

    if args.export_journeys_csv:
        conn = connect(settings.db_path)
        try:
            output_path, journeys_count, sessions_count = export_customer_journeys_csv(
                conn=conn,
                output_path=Path(args.journeys_csv_path),
                start_date=args.start_date,
                end_date=args.end_date,
                max_journeys=settings.ihc_max_journeys_per_run,
            )
        finally:
            conn.close()

        print(
            json.dumps(
                {
                    "journeys_csv_path": str(output_path.resolve()),
                    "journeys_count": journeys_count,
                    "sessions_count": sessions_count,
                },
                indent=2,
            )
        )
        return

    result = run_pipeline(
        settings=settings,
        start_date=args.start_date,
        end_date=args.end_date,
        use_mock_api=args.mock_api,
    )

    print(json.dumps(result.__dict__, indent=2))


if __name__ == "__main__":
    main()
