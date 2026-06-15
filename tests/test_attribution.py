from __future__ import annotations

from src.tasks.attribution import (
    chunked,
    normalize_attribution_rows,
    validate_ihc_sums,
)


def test_chunked_respects_journey_limit() -> None:
    rows = [
        {"conversion_id": "c1", "session_id": "s1"},
        {"conversion_id": "c1", "session_id": "s2"},
        {"conversion_id": "c2", "session_id": "s3"},
        {"conversion_id": "c3", "session_id": "s4"},
    ]

    chunks = list(chunked(rows, size=2))

    assert len(chunks) == 2
    first_ids = {r["conversion_id"] for r in chunks[0]}
    second_ids = {r["conversion_id"] for r in chunks[1]}
    assert first_ids == {"c1", "c2"}
    assert second_ids == {"c3"}


def test_chunked_respects_session_limit() -> None:
    rows = [
        {"conversion_id": "c1", "session_id": "s1"},
        {"conversion_id": "c1", "session_id": "s2"},
        {"conversion_id": "c2", "session_id": "s3"},
        {"conversion_id": "c2", "session_id": "s4"},
        {"conversion_id": "c3", "session_id": "s5"},
    ]

    chunks = list(chunked(rows, size=10, max_sessions_per_request=3))

    assert len(chunks) == 2
    assert len(chunks[0]) <= 3
    assert len(chunks[1]) <= 3


def test_normalize_attribution_rows_supports_conversion_id_key() -> None:
    rows = [
        {"conversion_id": "c1", "session_id": "s1", "ihc": 0.4},
        {"conv_id": "c1", "session_id": "s2", "ihc": 0.6},
    ]

    normalized = normalize_attribution_rows(rows)

    assert normalized == [("c1", "s1", 0.4), ("c1", "s2", 0.6)]


def test_validate_ihc_sums_flags_invalid_conversions() -> None:
    rows = [("c1", "s1", 0.4), ("c1", "s2", 0.5), ("c2", "s3", 1.0)]

    invalid = validate_ihc_sums(rows, tolerance=1e-6)

    assert invalid == [("c1", 0.9)]
