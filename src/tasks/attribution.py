from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from src.ihc_client import IhcClient



def chunked(
    items: list[dict[str, Any]],
    size: int,
    max_sessions_per_request: int | None = None,
) -> Iterable[list[dict[str, Any]]]:
    """Yield request batches constrained by journey and session limits.

    Args:
        items: Flat session-level payload rows.
        size: Maximum number of unique journeys (`conversion_id`) per chunk.
        max_sessions_per_request: Optional session cap per chunk.

    Yields:
        Lists of session rows ready to be sent in one API request.
    """
    if size <= 0:
        yield items
        return

    by_conversion: dict[str, list[dict[str, Any]]] = {}
    order: list[str] = []

    for row in items:
        conversion_id = str(row.get("conversion_id", ""))
        if not conversion_id:
            continue

        if conversion_id not in by_conversion:
            by_conversion[conversion_id] = []
            order.append(conversion_id)

        by_conversion[conversion_id].append(row)

    session_limit = max_sessions_per_request if max_sessions_per_request and max_sessions_per_request > 0 else None
    chunk: list[dict[str, Any]] = []
    chunk_journeys = 0
    chunk_sessions = 0

    for conversion_id in order:
        journey_rows = by_conversion[conversion_id]
        next_sessions = len(journey_rows)
        hit_journey_limit = chunk_journeys >= size
        hit_session_limit = session_limit is not None and chunk_sessions > 0 and (chunk_sessions + next_sessions) > session_limit

        if hit_journey_limit or hit_session_limit:
            yield chunk
            chunk = []
            chunk_journeys = 0
            chunk_sessions = 0

        chunk.extend(journey_rows)
        chunk_journeys += 1
        chunk_sessions += next_sessions

    if chunk:
        yield chunk



def score_with_mock(journeys: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Compute deterministic attribution locally for testing.

    Args:
        journeys: Flat IHC-format session rows.

    Returns:
        Session-level attribution rows with `conversion_id`, `session_id`, `ihc`.
    """
    rows: list[dict[str, Any]] = []

    by_conversion: dict[str, list[dict[str, Any]]] = {}
    for row in journeys:
        conversion_id = str(row.get("conversion_id", ""))
        if not conversion_id:
            continue
        by_conversion.setdefault(conversion_id, []).append(row)

    for conversion_id, touchpoints in by_conversion.items():
        scores = []
        for tp in touchpoints:
            score = (
                1.0
                + float(tp.get("holder_engagement", 0))
                + (2.0 * float(tp.get("closer_engagement", 0)))
                + (0.5 * float(tp.get("impression_interaction", 0)))
            )
            scores.append(score)

        denom = sum(scores)
        if denom <= 0:
            denom = float(len(scores))
            scores = [1.0] * len(scores)

        for tp, score in zip(touchpoints, scores):
            rows.append(
                {
                    "conversion_id": conversion_id,
                    "session_id": str(tp.get("session_id", "")),
                    "ihc": score / denom,
                }
            )

    return rows



def score_customer_journeys(
    journeys: list[dict[str, Any]],
    client: IhcClient,
    chunk_size: int,
    max_sessions_per_request: int | None = None,
    use_mock: bool = False,
) -> list[dict[str, Any]]:
    """Score journeys either via mock logic or live IHC API calls.

    Args:
        journeys: Flat session rows in IHC payload format.
        client: Configured IHC client for live API requests.
        chunk_size: Max journeys per API request.
        max_sessions_per_request: Optional max session rows per request.
        use_mock: If true, use local deterministic scoring.

    Returns:
        Session-level attribution result rows.
    """
    if not journeys:
        return []

    if use_mock:
        return score_with_mock(journeys)

    rows: list[dict[str, Any]] = []
    for chunk in chunked(journeys, chunk_size, max_sessions_per_request=max_sessions_per_request):
        rows.extend(client.score_journeys(chunk))
    return rows



def normalize_attribution_rows(rows: list[dict[str, Any]]) -> list[tuple[str, str, float]]:
    """Normalize attribution response rows into DB-write tuples.

    Args:
        rows: Attribution dictionaries from mock or IHC API.

    Returns:
        List of `(conv_id, session_id, ihc)` tuples.
    """
    normalized: list[tuple[str, str, float]] = []
    for row in rows:
        conv_id = str(row.get("conv_id", row.get("conversion_id", "")))
        session_id = str(row.get("session_id", ""))
        ihc = float(row.get("ihc", 0.0))

        if not conv_id or not session_id:
            continue

        normalized.append((conv_id, session_id, ihc))

    return normalized



def validate_ihc_sums(
    rows: list[tuple[str, str, float]], tolerance: float = 1e-3
) -> list[tuple[str, float]]:
    """Validate that attribution sums to 1 per conversion.

    Args:
        rows: Normalized attribution tuples.
        tolerance: Allowed absolute deviation from total attribution of 1.

    Returns:
        List of `(conv_id, total_ihc)` for invalid conversions.
    """
    totals: dict[str, float] = {}
    for conv_id, _, ihc in rows:
        totals[conv_id] = totals.get(conv_id, 0.0) + ihc

    invalid: list[tuple[str, float]] = []
    for conv_id, total in totals.items():
        if abs(total - 1.0) > tolerance:
            invalid.append((conv_id, total))

    return invalid
