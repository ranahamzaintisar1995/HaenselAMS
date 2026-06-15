# Attribution Pipeline (IHC)

## Project Scope
This project implements the full attribution pipeline:
- Query source data from SQLite (`session_sources`, `conversions`, `session_costs`)
- Build customer journeys per conversion
- Transform journeys into IHC API format
- Send journeys to IHC API in compliant batches
- Write returned attribution (`ihc`) to `attribution_customer_journey`
- Build `channel_reporting`
- Export `channel_reporting.csv` with `CPO` and `ROAS`

## Pipeline Design
The code is modular and task-oriented so it can be orchestrated later (for example with Airflow):
1. Schema setup (`challenge_db_create.sql`)
2. Journey extraction (`session_sources` + `conversions`)
3. Payload transformation to IHC format
4. IHC API batching and request execution
5. Attribution persistence to DB
6. Channel reporting aggregation
7. CSV export

Main entry point:
- `main.py`

Core modules:
- `src/tasks/extract_journeys.py`
- `src/tasks/attribution.py`
- `src/ihc_client.py`
- `src/tasks/reporting.py`
- `src/pipeline.py`

## IHC API Integration
Working API setup:
- Endpoint: `https://api.ihc-attribution.com/v1/compute_ihc`
- Method: `POST`
- Header: `x-api-key`
- URL parameter: `conv_type_id`
- Body:
  - `customer_journeys` (required)
  - `redistribution_parameter` (optional)

Expected response object keys:
- `statusCode`
- `partialFailureErrors`
- `value`

The pipeline reads attribution rows from `value` and writes `(conv_id, session_id, ihc)` into `attribution_customer_journey`.

## Customer Journey Transformation Format
Each row sent to IHC is session-level and includes:
- `conversion_id`
- `session_id`
- `timestamp`
- `channel_label`
- `holder_engagement`
- `closer_engagement`
- `conversion`
- `impression_interaction`

Export command for upload-ready training CSV:
- `python main.py --export-journeys-csv`

Generated file:
- `ihc_customer_journeys.csv`

Full export (all journeys) created in this project:
- `ihc_customer_journeys_full.csv`

## Batching and Limits
The pipeline now supports all journeys with compliant chunking:
- `IHC_MAX_JOURNEYS_PER_RUN=0` means no total cap
- `IHC_CHUNK_SIZE=100` targets 100 journeys per call
- `IHC_MAX_SESSIONS_PER_REQUEST=200` enforces free-plan session cap

Batching is constrained by both journeys and sessions, so each request stays within IHC limits.

## Run Instructions
Full pipeline:
- `python main.py`

Mock mode (no external API):
- `python main.py --mock-api`

Export upload-ready journeys CSV:
- `python main.py --export-journeys-csv`

## Tests
Run all tests:
- `.venv/bin/pytest -q`

Run a single test file:
- `.venv/bin/pytest -q tests/test_attribution.py`

Current basic suite covers transformation, batching, response parsing, and
attribution validation logic.

## CI/CD (GitHub Actions)
This project includes two workflows:
- CI: `.github/workflows/ci.yml`
  - Triggers on push, PR, and manual run
  - Installs dependencies and runs `pytest -q`

- CD: `.github/workflows/cd.yml`
  - Manual trigger (`workflow_dispatch`)
  - Runs pipeline in `mock` or `live` mode
  - Uploads `channel_reporting.csv` as an artifact

Required repository secrets for live mode:
- `IHC_API_KEY`
- `IHC_CONV_TYPE_ID`

## Assumptions
- Source date/time values can be compared reliably using SQLite `datetime(...)`
- Missing session costs are treated as `0`
- `CPO` and `ROAS` are `NaN` when denominator is `0`
- IHC output rows include `conversion_id`, `session_id`, and `ihc`

## What Can Be Improved
- Add retry/backoff and dead-letter strategy for failed API chunks
- Add stricter request/response schema validation
- Add automated tests for transformation and KPI calculations
- Add orchestration DAG and monitoring/alerting
- Add incremental processing with watermarking
